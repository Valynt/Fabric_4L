import { RuleTester } from "eslint";
import rule from "../no-imperative-navigation";

const ruleTester = new RuleTester({
  languageOptions: {
    parserOptions: {
      ecmaVersion: 2020,
      sourceType: "module",
    },
  },
});

ruleTester.run("no-imperative-navigation", rule, {
  valid: [
    // Valid: no navigation calls
    {
      code: `function handleClick() { console.log("clicked"); }`,
    },
    // Valid: other method calls
    {
      code: `app.get('/api/users', handler);`,
    },
    // Valid: non-router push
    {
      code: `array.push(item);`,
    },
    // Valid: canonical navigation service implementation in the route manifest
    {
      code: `class NavigationService { back() { return this.navigate("dashboard"); } }`,
      filename: "examples/canonical/ui/route-manifest.ts",
    },
    // Valid: exported helper delegates through canonical navigation service in the route manifest
    {
      code: `function navigate(state) { return navigationService.navigate(state); }`,
      filename: "examples/canonical/ui/route-manifest.ts",
    },
  ],
  invalid: [
    // Invalid: router.push
    {
      code: `router.push('/dashboard');`,
      errors: [{ messageId: "noImperativeNavigation" }],
    },
    // Invalid: history.push
    {
      code: `history.push('/profile');`,
      errors: [{ messageId: "noImperativeNavigation" }],
    },
    // Invalid: navigate function
    {
      code: `navigate('/home');`,
      errors: [{ messageId: "noImperativeNavigation" }],
    },
    // Invalid: app.navigate
    {
      code: `app.navigate('/settings');`,
      errors: [{ messageId: "noImperativeNavigation" }],
    },
    // Invalid: lookalike class methods outside the canonical route manifest
    {
      code: `class OtherService { back() { return this.navigate("dashboard"); } }`,
      filename: "apps/web/src/features/OtherService.ts",
      errors: [{ messageId: "noImperativeNavigation" }],
    },
    // Invalid: unrelated objects named navigationService outside the canonical route manifest
    {
      code: `function go() { return navigationService.navigate("dashboard"); }`,
      filename: "apps/web/src/features/go.ts",
      errors: [{ messageId: "noImperativeNavigation" }],
    },
  ],
});
