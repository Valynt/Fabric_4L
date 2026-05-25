#!/usr/bin/env bash
# Key Rotation Runbook - Interactive script for secure API key rotation
# Usage: ./scripts/security/rotation-runbook.sh

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

confirm() {
    local message=$1
    echo ""
    read -p "$message [y/N] " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    print_header "Step 1: Prerequisites Check"
    
    local all_good=true
    
    # Check Infisical CLI
    if command -v infisical &> /dev/null; then
        print_success "Infisical CLI found"
        infisical --version 2>/dev/null || true
    else
        print_error "Infisical CLI not found"
        print_info "Install: https://infisical.com/docs/cli/overview"
        all_good=false
    fi
    
    # Check Python
    if command -v python3 &> /dev/null; then
        print_success "Python found: $(python3 --version)"
    else
        print_error "Python 3 not found"
        all_good=false
    fi
    
    # Check Infisical auth
    if infisical user 2>/dev/null | grep -q "email"; then
        print_success "Authenticated with Infisical"
    else
        print_error "Not logged in to Infisical"
        print_info "Run: infisical login"
        all_good=false
    fi
    
    # Check kubectl (for production)
    if command -v kubectl &> /dev/null; then
        print_success "kubectl found"
    else
        print_warning "kubectl not found (required for production restarts)"
    fi
    
    if [ "$all_good" = false ]; then
        print_error "Some prerequisites missing. Please install and retry."
        exit 1
    fi
    
    print_success "All prerequisites met"
}

# Select provider
select_provider() {
    print_header "Step 2: Select Provider"
    
    echo "Select which API key to rotate:"
    echo "  1) OpenAI"
    echo "  2) Clerk"
    echo "  3) Thesys"
    echo "  4) Registry (GitHub PAT)"
    echo "  5) All providers"
    echo ""
    
    read -p "Enter number [1-5]: " choice
    
    case $choice in
        1) PROVIDER="openai" ;;
        2) PROVIDER="clerk" ;;
        3) PROVIDER="thesys" ;;
        4) PROVIDER="registry" ;;
        5) PROVIDER="all" ;;
        *) 
            print_error "Invalid choice"
            exit 1
            ;;
    esac
    
    print_success "Selected: $PROVIDER"
}

# Select environment
select_environment() {
    print_header "Step 3: Select Environment"
    
    echo "Select target environment:"
    echo "  1) dev (local development)"
    echo "  2) staging"
    echo "  3) prod (production)"
    echo ""
    
    read -p "Enter number [1-3]: " choice
    
    case $choice in
        1) ENV="dev" ;;
        2) ENV="staging" ;;
        3) ENV="prod" ;;
        *) 
            print_error "Invalid choice"
            exit 1
            ;;
    esac
    
    print_success "Selected environment: $ENV"
    
    if [ "$ENV" = "prod" ]; then
        print_warning "PRODUCTION ENVIRONMENT SELECTED"
        print_warning "This will affect live services!"
        
        if ! confirm "Are you sure you want to rotate keys in PRODUCTION?"; then
            print_info "Cancelled"
            exit 0
        fi
        
        # Additional confirmation for production
        read -p "Type 'ROTATE-PROD' to confirm: " confirm_text
        if [ "$confirm_text" != "ROTATE-PROD" ]; then
            print_error "Confirmation failed"
            exit 1
        fi
    fi
}

# Get manual key input
get_manual_key() {
    local provider=$1
    local env_var_name=""
    local dashboard_url=""
    
    case $provider in
        openai)
            env_var_name="OPENAI_MANUAL_KEY"
            dashboard_url="https://platform.openai.com/account/api-keys"
            ;;
        clerk)
            env_var_name="CLERK_MANUAL_KEY"
            dashboard_url="https://dashboard.clerk.com"
            ;;
        thesys)
            env_var_name="THESYS_MANUAL_KEY"
            dashboard_url="Thesys dashboard (internal)"
            ;;
        registry)
            env_var_name="REGISTRY_MANUAL_KEY"
            dashboard_url="https://github.com/settings/tokens"
            ;;
    esac
    
    print_header "Step 4: Generate New Key - $provider"
    
    print_info "Please generate a new $provider key:"
    echo "  Dashboard: $dashboard_url"
    echo ""
    
    case $provider in
        openai)
            echo "Steps:"
            echo "  1. Click 'Create new secret key'"
            echo "  2. Name it: fabric4l-${ENV}-$(date +%Y-%m-%d)"
            echo "  3. Copy the key (shown only once)"
            ;;
        clerk)
            echo "Steps:"
            echo "  1. Select your instance"
            echo "  2. Go to API Keys → Secret Keys"
            echo "  3. Click 'Add secret key'"
            echo "  4. Copy the key"
            ;;
        thesys)
            echo "Steps:"
            echo "  1. Navigate to API Keys section"
            echo "  2. Generate new key"
            echo "  3. Copy the key"
            ;;
        registry)
            echo "Steps:"
            echo "  1. Click 'Generate new token'"
            echo "  2. Select scopes: read:packages, write:packages"
            echo "  3. Generate and copy the token"
            ;;
    esac
    
    echo ""
    
    # Check if already set in environment
    current_value="${!env_var_name:-}"
    if [ -n "$current_value" ]; then
        print_success "$env_var_name is already set in environment"
        if confirm "Use existing value?"; then
            return 0
        fi
    fi
    
    # Prompt for key
    read -s -p "Paste the new key (input hidden): " new_key
    echo ""
    
    if [ -z "$new_key" ]; then
        print_error "No key provided"
        exit 1
    fi
    
    # Validate key format
    case $provider in
        openai)
            if [[ ! $new_key =~ ^sk- ]]; then
                print_error "Invalid OpenAI key format (must start with 'sk-')"
                exit 1
            fi
            ;;
        clerk)
            if [[ ! $new_key =~ ^sk_(test|live)_ ]]; then
                print_error "Invalid Clerk key format (must start with 'sk_test_' or 'sk_live_')"
                exit 1
            fi
            ;;
        registry)
            if [[ ! $new_key =~ ^(ghp_|github_pat_) ]]; then
                print_error "Invalid GitHub token format"
                exit 1
            fi
            ;;
    esac
    
    # Export for rotation script
    export "$env_var_name=$new_key"
    print_success "Key captured and validated"
}

# Run dry-run first
run_dry_run() {
    print_header "Step 5: Dry Run"
    
    print_info "Running dry-run to preview changes..."
    echo ""
    
    python "${PROJECT_ROOT}/scripts/security/key_rotation.py" \
        --provider "$PROVIDER" \
        --env "$ENV" \
        --dry-run \
        --verbose
    
    echo ""
    
    if ! confirm "Does the dry-run output look correct?"; then
        print_error "Cancelled by user"
        exit 1
    fi
    
    print_success "Dry-run approved"
}

# Execute rotation
execute_rotation() {
    print_header "Step 6: Execute Rotation"
    
    if ! confirm "Execute LIVE rotation? This will update Infisical secrets"; then
        print_info "Cancelled"
        exit 0
    fi
    
    print_info "Executing rotation..."
    echo ""
    
    python "${PROJECT_ROOT}/scripts/security/key_rotation.py" \
        --provider "$PROVIDER" \
        --env "$ENV" \
        --audit-log "rotation_audit_${PROVIDER}_${ENV}_$(date +%Y%m%d_%H%M%S).json"
    
    if [ $? -ne 0 ]; then
        print_error "Rotation failed!"
        print_info "Check the output above for errors"
        exit 1
    fi
    
    print_success "Rotation completed"
}

# Verify keys
verify_rotation() {
    print_header "Step 7: Verification"
    
    print_info "Verifying new keys are working..."
    echo ""
    
    python "${PROJECT_ROOT}/scripts/security/verify-keys.py" \
        --provider "$PROVIDER" \
        --env "$ENV" \
        --detailed
    
    if [ $? -ne 0 ]; then
        print_warning "Some verifications failed"
        print_info "Review the output above"
        
        if ! confirm "Continue to next step?"; then
            exit 1
        fi
    else
        print_success "All verifications passed"
    fi
}

# Revoke old keys
revoke_old_keys() {
    print_header "Step 8: Revoke Old Keys"
    
    print_warning "IMPORTANT: Only revoke old keys after confirming new keys work!"
    print_info "New keys have been verified and services are using them."
    echo ""
    
    case $PROVIDER in
        openai)
            echo "Revoke old OpenAI key:"
            echo "  1. Visit: https://platform.openai.com/account/api-keys"
            echo "  2. Find the old key"
            echo "  3. Click the trash icon to delete"
            ;;
        clerk)
            echo "Revoke old Clerk key:"
            echo "  1. Visit: https://dashboard.clerk.com"
            echo "  2. Go to API Keys → Secret Keys"
            echo "  3. Find and revoke the old key"
            ;;
        thesys)
            echo "Revoke old Thesys key:"
            echo "  1. Visit Thesys dashboard"
            echo "  2. Navigate to API Keys"
            echo "  3. Revoke the old key"
            ;;
        registry)
            echo "Revoke old GitHub token:"
            echo "  1. Visit: https://github.com/settings/tokens"
            echo "  2. Find the old token"
            echo "  3. Click 'Delete'"
            ;;
        all)
            echo "Revoke old keys for all providers:"
            echo "  - OpenAI: https://platform.openai.com/account/api-keys"
            echo "  - Clerk: https://dashboard.clerk.com"
            echo "  - Thesys: Dashboard (internal)"
            echo "  - GitHub: https://github.com/settings/tokens"
            ;;
    esac
    
    echo ""
    
    if confirm "Have you revoked the old keys?"; then
        print_success "Old keys revoked"
    else
        print_warning "Please revoke old keys as soon as possible!"
        print_info "Old keys remain active and should be revoked within 24 hours"
    fi
}

# Final summary
final_summary() {
    print_header "Rotation Complete!"
    
    echo "Summary:"
    echo "  Provider: $PROVIDER"
    echo "  Environment: $ENV"
    echo "  Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""
    
    print_success "New keys are active and verified"
    print_info "Audit log saved to: rotation_audit_${PROVIDER}_${ENV}_*.json"
    
    echo ""
    echo "Next steps:"
    echo "  1. ✓ New keys generated and stored in Infisical"
    echo "  2. ✓ Services restarted with new keys"
    echo "  3. ✓ Keys verified working"
    echo "  4. ? Old keys revoked (your confirmation needed)"
    echo "  5. [ ] Update any external documentation"
    echo "  6. [ ] Monitor services for 24 hours"
    echo "  7. [ ] Keep audit log for compliance"
    echo ""
    
    print_info "For support, contact: security@fabric4l.com"
    print_info "Documentation: docs/security/key-rotation-guide.md"
}

# Main function
main() {
    clear
    
    print_header "🔐 Fabric4L API Key Rotation Runbook"
    echo "This script will guide you through rotating API keys securely."
    echo ""
    
    if ! confirm "Start key rotation process?"; then
        print_info "Cancelled"
        exit 0
    fi
    
    # Run all steps
    check_prerequisites
    select_provider
    select_environment
    
    # Get manual keys
    if [ "$PROVIDER" = "all" ]; then
        get_manual_key "openai"
        get_manual_key "clerk"
        get_manual_key "thesys"
        get_manual_key "registry"
    else
        get_manual_key "$PROVIDER"
    fi
    
    run_dry_run
    execute_rotation
    verify_rotation
    revoke_old_keys
    final_summary
}

# Run main
main "$@"
