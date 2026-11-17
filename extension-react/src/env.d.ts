declare const __VANTIQ_API_BASE__: string;

declare module "*.css?inline" {
  const content: string;
  export default content;
}
