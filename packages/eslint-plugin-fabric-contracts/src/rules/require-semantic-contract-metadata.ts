import { Rule } from "eslint";
import { asTSNode, RuleContext, TSESTree } from "../astTypes";

function propertyName(prop: TSESTree.Property): string | undefined {
  if (prop.key.type === "Identifier") return prop.key.name;
  if (prop.key.type === "Literal" && typeof prop.key.value === "string") return prop.key.value;
  return undefined;
}

function literalString(node: TSESTree.Node | null | undefined): string | undefined {
  if (!node) return undefined;
  if (node.type === "Literal" && typeof node.value === "string") return node.value;
  if (node.type === "MemberExpression" && node.property.type === "Identifier") return node.property.name;
  return undefined;
}

function objectProperty(node: TSESTree.ObjectExpression, name: string): TSESTree.Property | undefined {
  return node.properties.find((prop): prop is TSESTree.Property => {
    return prop.type === "Property" && propertyName(prop) === name;
  });
}

function hasSemanticContractMetadata(metadata: TSESTree.Node): boolean {
  if (metadata.type === "SpreadElement") return true;
  if (metadata.type !== "ObjectExpression") return false;
  return metadata.properties.some((prop) => {
    if (prop.type === "SpreadElement") return true;
    const name = propertyName(prop);
    return name === "semanticContractVersion" || name === "semanticContractValid" || name === "contractVersions";
  });
}

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Require semantic-contract metadata on AG-UI run completion events",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contracts/agent-registry/compatibility-matrix.json",
    },
    schema: [],
    messages: {
      requireSemanticContractMetadata:
        "AG-UI RUN_FINISHED events must include semantic-contract metadata. " +
        "Add semanticContractVersion, semanticContractValid, or contractVersions to metadata.",
    },
  },

  create(context: RuleContext): Rule.RuleListener {
    return {
      ObjectExpression(node): void {
        const object = asTSNode<TSESTree.ObjectExpression>(node);
        const typeProp = objectProperty(object, "type");
        const eventType = typeProp ? literalString(typeProp.value) : undefined;
        if (eventType !== "RUN_FINISHED") return;

        const metadataProp = objectProperty(object, "metadata");
        if (!metadataProp || !hasSemanticContractMetadata(metadataProp.value)) {
          context.report({ node, messageId: "requireSemanticContractMetadata" });
        }
      },
    };
  },
};

export = rule;
