import { RuleTester } from "eslint";
import rule from "../no-imperative-navigation";

const ruleTester = new RuleTester({
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
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
  ],
});
