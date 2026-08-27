import { Rule } from "eslint";
import { asTSNode, ParameterNode, RuleContext, TSESTree } from "../astTypes";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow tenantId as function parameters - use AsyncLocalStorage context",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contract.md#21-tenant-isolation-boundary",
    },
    schema: [],
    messages: {
      noTenantIdParameter:
        "{{parameterName}} is not allowed as a function parameter. " +
        "Tenant context must flow via AsyncLocalStorage (getCurrentTenant() from context/tenant-context.ts). " +
        "See contract.md §2.1 for canonical pattern.",
    },
  },

  create(context: RuleContext): Rule.RuleListener {
    const tenantIdPattern = /tenant[_-]?id/i;

    function reportParameter(node: TSESTree.Node, name: string): void {
      context.report({ node: node as never, messageId: "noTenantIdParameter", data: { parameterName: name } });
    }

    function checkParameter(param: ParameterNode): void {
      if (param.type === "Identifier" && tenantIdPattern.test(param.name)) reportParameter(param, param.name);
      else if (param.type === "ObjectPattern") {
        for (const prop of param.properties) {
          if (prop.type === "Property") {
            if (prop.key.type === "Identifier" && tenantIdPattern.test(prop.key.name)) reportParameter(prop.key, prop.key.name);
            if (prop.value.type === "ObjectPattern") checkParameter(prop.value);
          }
        }
      } else if (param.type === "ArrayPattern") {
        for (const element of param.elements) if (element) checkParameter(element as ParameterNode);
      } else if (param.type === "RestElement" && param.argument.type === "Identifier" && tenantIdPattern.test(param.argument.name)) reportParameter(param.argument, param.argument.name);
    }

    return {
      FunctionDeclaration(node): void {
        for (const param of asTSNode<TSESTree.FunctionDeclaration>(node).params) checkParameter(param);
      },
      FunctionExpression(node): void {
        for (const param of asTSNode<TSESTree.FunctionExpression>(node).params) checkParameter(param);
      },
      ArrowFunctionExpression(node): void {
        for (const param of asTSNode<TSESTree.ArrowFunctionExpression>(node).params) checkParameter(param);
      },
    };
  },
};

export = rule;
