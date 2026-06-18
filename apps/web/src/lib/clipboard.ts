/**
 * Clipboard utility.
 *
 * Wraps the native Clipboard API so tests can mock a single boundary instead of
 * the entire navigator object, which is read-only in jsdom.
 */
export async function copyToClipboard(text: string): Promise<void> {
  return navigator.clipboard.writeText(text);
}
