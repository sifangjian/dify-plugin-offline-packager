import pluginVue from "eslint-plugin-vue";
import vueTsEslintConfig from "@vue/eslint-config-typescript";

export default [
  ...pluginVue.configs["flat/recommended"],
  ...vueTsEslintConfig(),
  {
    ignores: ["dist/**", "package-lock.json"],
  },
  {
    rules: {
      "vue/multi-word-component-names": "off",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
];
