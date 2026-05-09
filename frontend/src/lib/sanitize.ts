export function sanitizeFilename(name: string): string {
  return name
    .replace(/[/\\?%*:|"<>]/g, '_')
    .replace(/\.\./g, '_')
    .slice(0, 255);
}

export function escapeForDisplay(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
