/**
 * ValuePack Detail Component
 * 
 * Displays complete ValuePack Framework v1.0 schema data.
 * Used for full ValuePack exploration and configuration.
 */
import { useState } from "react";
import {
  Building2,
  TrendingUp,
  Users,
  Calculator,
  Award,
  Target,
  Network,
  Shield,
  Clock,
  Database,
  Zap,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ValuePackFrameworkData } from "@/hooks/useValuePacks";
import { SectionCard } from "@/components/blocks/SectionCard";
import { Btn } from "@/components/ui/fabric";

interface ValuePackDetailProps {
  valuepack: ValuePackFrameworkData;
  className?: string;
  onUseTemplate?: (templateId: string) => void;
  onApplyToDeal?: () => void;
}

const tierConfig = {
  1: { label: "Tier 1: Immediate Traction", color: "bg-success/10 text-success border-success/20" },
  2: { label: "Tier 2: High ROI, Underserved", color: "bg-primary/10 text-primary border-primary/20" },
  3: { label: "Tier 3: Complex but Powerful", color: "bg-primary/10 text-primary border-primary/20" },
};

export function ValuePackDetail({
  valuepack,
  className,
  onUseTemplate,
  onApplyToDeal,
}: ValuePackDetailProps) {
  const tier = tierConfig[valuepack.tier];

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{valuepack.display_name}</h1>
          <p className="text-muted-foreground mt-1">{valuepack.description}</p>
          <div className="flex items-center gap-2 mt-3">
            <Badge className={cn(tier.color, "border")}>{tier.label}</Badge>
            {valuepack.completeness_score !== undefined && (
              <Badge variant="outline" className="text-xs">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                {Math.round(valuepack.completeness_score * 100)}% Complete
              </Badge>
            )}
          </div>
        </div>
        {onApplyToDeal && (
          <Btn variant="primary" onClick={onApplyToDeal}>
            Apply to Deal
          </Btn>
        )}
      </div>

      {/* Metadata Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MetadataCard
          icon={<Building2 className="w-4 h-4" />}
          label="Deal Size"
          value={valuepack.metadata.deal_size_range}
        />
        <MetadataCard
          icon={<Clock className="w-4 h-4" />}
          label="Sales Cycle"
          value={valuepack.metadata.sales_cycle_length}
        />
        <MetadataCard
          icon={<Zap className="w-4 h-4" />}
          label="Switching Cost"
          value={valuepack.metadata.switching_cost}
          capitalize
        />
        <MetadataCard
          icon={<Database className="w-4 h-4" />}
          label="Data Richness"
          value={valuepack.metadata.data_richness}
          capitalize
        />
        <MetadataCard
          icon={<TrendingUp className="w-4 h-4" />}
          label="Feedback Speed"
          value={valuepack.metadata.feedback_loop_speed}
          capitalize
        />
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="drivers" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="drivers">Drivers</TabsTrigger>
          <TabsTrigger value="usecases">Use Cases</TabsTrigger>
          <TabsTrigger value="models">Models</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="evidence">Evidence</TabsTrigger>
        </TabsList>

        <TabsContent value="drivers" className="mt-4">
          <SectionCard title="Primary Value Drivers" subtitle={`${valuepack.primary_value_drivers.length} drivers that move money in this industry`}>
            <div className="space-y-4">
              {valuepack.primary_value_drivers.map((driver) => (
                <ValueDriverCard key={driver.id} driver={driver} />
              ))}
            </div>
          </SectionCard>
        </TabsContent>

        <TabsContent value="usecases" className="mt-4">
          <SectionCard title="Core Use Cases" subtitle={`${valuepack.core_use_cases.length} use cases that customers buy`}>
            <div className="grid gap-4">
              {valuepack.core_use_cases.map((useCase) => (
                <UseCaseCard key={useCase.id} useCase={useCase} />
              ))}
            </div>
          </SectionCard>
        </TabsContent>

        <TabsContent value="models" className="mt-4">
          <SectionCard title="Economic Model Types" subtitle={`${valuepack.economic_model_types.length} calculation patterns`}>
            <div className="space-y-4">
              {valuepack.economic_model_types.map((model) => (
                <EconomicModelCard key={model.id} model={model} />
              ))}
            </div>
          </SectionCard>
        </TabsContent>

        <TabsContent value="templates" className="mt-4">
          <SectionCard title="Composable Model Templates" subtitle="Reusable calculation patterns">
            <div className="space-y-4">
              {valuepack.composable_model_templates.map((template) => (
                <TemplateCard
                  key={template.template_id}
                  template={template}
                  onUse={onUseTemplate ? () => onUseTemplate(template.template_id) : undefined}
                />
              ))}
            </div>
          </SectionCard>
        </TabsContent>

        <TabsContent value="evidence" className="mt-4 space-y-4">
          <SectionCard title="Proof Requirements" subtitle="What makes value claims credible">
            <div className="space-y-3">
              {valuepack.proof_requirements?.map((req) => req && (
                <div key={req.id} className="flex items-start gap-3 p-3 border rounded-lg">
                  <Shield className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-sm">{req.requirement}</p>
                    <p className="text-xs text-muted-foreground">{req.evidence_type}</p>
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Why This Platform Wins" subtitle="Differentiated value propositions">
            <div className="space-y-3">
              {valuepack.why_it_wins.map((win, idx) => (
                <div key={idx} className="p-3 border rounded-lg bg-primary/5">
                  <p className="font-medium text-sm text-foreground">{win.statement}</p>
                  <p className="text-xs text-muted-foreground mt-1">{win.differentiation}</p>
                  <p className="text-xs text-primary mt-1">Proof: {win.proof_point}</p>
                </div>
              ))}
            </div>
          </SectionCard>

          {valuepack.pre_wired_ontology_tags && (
            <SectionCard title="Ontology Tags" subtitle="Taxonomy for cross-industry linkage">
              <div className="flex flex-wrap gap-2">
                {valuepack.pre_wired_ontology_tags.map((tag) => (
                  <Badge key={tag.tag} variant="secondary" className="text-xs">
                    {tag.tag}
                  </Badge>
                ))}
              </div>
            </SectionCard>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function MetadataCard({
  icon,
  label,
  value,
  capitalize,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  capitalize?: boolean;
}) {
  return (
    <div className="p-3 border rounded-lg bg-card">
      <div className="flex items-center gap-2 text-muted-foreground mb-1">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className={cn("text-sm font-medium", capitalize && "capitalize")}>{value}</p>
    </div>
  );
}

function ValueDriverCard({ driver }: { driver: ValuePackFrameworkData["primary_value_drivers"][0] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
            <TrendingUp className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h4 className="font-medium text-foreground">{driver.name}</h4>
            <p className="text-sm text-muted-foreground mt-0.5">{driver.description}</p>
          </div>
        </div>
        <Badge variant="outline" className="shrink-0 text-xs">
          {driver.typical_impact}
        </Badge>
      </div>
      
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-primary mt-3 hover:underline"
      >
        {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        {expanded ? "Hide details" : "Show measurement approach"}
      </button>
      
      {expanded && (
        <div className="mt-3 pt-3 border-t text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Measurement:</span> {driver.measurement_approach}
        </div>
      )}
    </div>
  );
}

function UseCaseCard({ useCase }: { useCase: ValuePackFrameworkData["core_use_cases"][0] }) {
  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
          <Target className="w-4 h-4 text-primary" />
        </div>
        <div className="flex-1">
          <h4 className="font-medium text-foreground">{useCase.name}</h4>
          <p className="text-sm text-muted-foreground mt-0.5">{useCase.description}</p>
          <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {useCase.target_persona}
            </span>
          </div>
          <p className="text-xs text-foreground mt-2 bg-muted p-2 rounded">
            <span className="font-medium">Problem:</span> {useCase.business_problem}
          </p>
        </div>
      </div>
    </div>
  );
}

function EconomicModelCard({ model }: { model: ValuePackFrameworkData["economic_model_types"][0] }) {
  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-success/10 flex items-center justify-center shrink-0">
          <Calculator className="w-4 h-4 text-success" />
        </div>
        <div className="flex-1">
          <h4 className="font-medium text-foreground">{model.name}</h4>
          <p className="text-sm text-muted-foreground mt-0.5">{model.formula_shape}</p>
          
          <div className="mt-3">
            <p className="text-xs text-muted-foreground mb-2">Required inputs:</p>
            <div className="flex flex-wrap gap-1.5">
              {model.inputs.map((input) => (
                <code key={input} className="text-xs bg-muted px-1.5 py-0.5 rounded">
                  {input}
                </code>
              ))}
            </div>
          </div>
          
          <div className="flex items-center gap-4 mt-3 text-xs">
            <span className="text-muted-foreground">
              Output: <span className="font-medium text-foreground">{model.output_unit}</span>
            </span>
            {model.typical_range && (
              <span className="text-muted-foreground">
                Range: <span className="font-medium text-foreground">{model.typical_range}</span>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function TemplateCard({
  template,
  onUse,
}: {
  template: ValuePackFrameworkData["composable_model_templates"][0];
  onUse?: () => void;
}) {
  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
            <Network className="w-4 h-4 text-primary" />
          </div>
          <div className="flex-1">
            <h4 className="font-medium text-foreground">{template.template_name}</h4>
            <p className="text-sm text-muted-foreground mt-0.5">{template.formula_pattern}</p>
            
            <div className="mt-2 p-2 bg-muted rounded text-xs">
              <span className="font-medium">Example:</span> {template.example_calculation}
            </div>
            
            <div className="mt-2">
              <span className="text-xs text-muted-foreground">
                Used in {template.applicable_industries.length} industries
              </span>
            </div>
          </div>
        </div>
        {onUse && (
          <Btn variant="outline" className="shrink-0" onClick={onUse}>
            Use Template
          </Btn>
        )}
      </div>
    </div>
  );
}
