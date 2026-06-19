import React from 'react';

interface MarkdownRendererProps {
  content: string;
}

/**
 * Normalizes LLM markdown output by:
 * 1. Stripping common leading indentation
 * 2. Normalizing indented list items (4-space indent → 0)
 * 3. Converting markdown to clean React elements with explicit styling
 */
function parseMarkdown(raw: string): React.ReactNode[] {
  // Step 1: Normalize line endings and trim
  let text = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();

  // Step 2: Strip common leading whitespace from all lines
  const lines = text.split('\n');
  const nonBlankLines = lines.filter(l => l.trim().length > 0);
  if (nonBlankLines.length > 0) {
    const minIndent = Math.min(
      ...nonBlankLines.map(l => {
        const m = l.match(/^(\s*)/);
        return m ? m[1].length : 0;
      })
    );
    if (minIndent > 0) {
      text = lines.map(l => l.slice(minIndent)).join('\n');
    }
  }

  // Step 3: Further strip remaining leading spaces from list items 
  // (handles cases where LLM indents list items with 2–4 spaces)
  text = text
    .split('\n')
    .map(line => {
      // If line starts with spaces then a list marker, strip the spaces
      return line.replace(/^(\s{1,8})([-*+]\s)/, '$2');
    })
    .join('\n');

  // Step 4: Parse line by line into React elements
  const normalizedLines = text.split('\n');
  const nodes: React.ReactNode[] = [];
  let i = 0;

  const inlineFormat = (txt: string): React.ReactNode[] => {
    // Handle bold+italic, bold, italic, inline code
    const parts: React.ReactNode[] = [];
    const regex = /(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
    let last = 0;
    let match;
    while ((match = regex.exec(txt)) !== null) {
      if (match.index > last) parts.push(txt.slice(last, match.index));
      if (match[2]) parts.push(<strong key={match.index}><em>{match[2]}</em></strong>);
      else if (match[3]) parts.push(<strong key={match.index}>{match[3]}</strong>);
      else if (match[4]) parts.push(<em key={match.index}>{match[4]}</em>);
      else if (match[5]) parts.push(<code key={match.index} style={{ background: '#f1f5f9', padding: '1px 5px', borderRadius: 4, fontSize: '0.85em', fontFamily: 'monospace', color: '#1e293b' }}>{match[5]}</code>);
      last = match.index + match[0].length;
    }
    if (last < txt.length) parts.push(txt.slice(last));
    return parts;
  };

  while (i < normalizedLines.length) {
    const line = normalizedLines[i];

    // Blank line
    if (line.trim() === '') {
      i++;
      continue;
    }

    // H1
    if (/^# /.test(line)) {
      nodes.push(
        <h1 key={i} style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a', margin: '1.5rem 0 0.6rem', paddingBottom: '0.4rem', borderBottom: '2px solid #e2e8f0', letterSpacing: '-0.01em' }}>
          {inlineFormat(line.replace(/^# /, ''))}
        </h1>
      );
      i++;
      continue;
    }

    // H2
    if (/^## /.test(line)) {
      nodes.push(
        <h2 key={i} style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a', margin: '1.25rem 0 0.5rem', paddingBottom: '0.3rem', borderBottom: '1px solid #e2e8f0', letterSpacing: '-0.01em' }}>
          {inlineFormat(line.replace(/^## /, ''))}
        </h2>
      );
      i++;
      continue;
    }

    // H3
    if (/^### /.test(line)) {
      nodes.push(
        <h3 key={i} style={{ fontSize: '0.95rem', fontWeight: 600, color: '#1e293b', margin: '1rem 0 0.35rem', letterSpacing: '0' }}>
          {inlineFormat(line.replace(/^### /, ''))}
        </h3>
      );
      i++;
      continue;
    }

    // H4
    if (/^#### /.test(line)) {
      nodes.push(
        <h4 key={i} style={{ fontSize: '0.875rem', fontWeight: 600, color: '#334155', margin: '0.75rem 0 0.25rem' }}>
          {inlineFormat(line.replace(/^#### /, ''))}
        </h4>
      );
      i++;
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim()) || /^\*\*\*+$/.test(line.trim())) {
      nodes.push(<hr key={i} style={{ border: 'none', borderTop: '1px solid #e2e8f0', margin: '1rem 0' }} />);
      i++;
      continue;
    }

    // Blockquote
    if (/^> /.test(line)) {
      nodes.push(
        <blockquote key={i} style={{ borderLeft: '4px solid #818cf8', paddingLeft: '1rem', paddingTop: '0.25rem', paddingBottom: '0.25rem', margin: '0.75rem 0', background: '#f5f3ff', borderRadius: '0 6px 6px 0', color: '#4b5563', fontStyle: 'italic' }}>
          {inlineFormat(line.replace(/^> /, ''))}
        </blockquote>
      );
      i++;
      continue;
    }

    // Unordered list (accumulate consecutive items)
    if (/^[-*+] /.test(line)) {
      const items: React.ReactNode[] = [];
      while (i < normalizedLines.length && /^[-*+] /.test(normalizedLines[i])) {
        items.push(
          <li key={i} style={{ marginBottom: '0.3rem', color: '#374151', paddingLeft: '0.15rem' }}>
            {inlineFormat(normalizedLines[i].replace(/^[-*+] /, ''))}
          </li>
        );
        i++;
      }
      nodes.push(
        <ul key={`ul-${i}`} style={{ listStyleType: 'disc', paddingLeft: '1.5rem', margin: '0.5rem 0 0.75rem' }}>
          {items}
        </ul>
      );
      continue;
    }

    // Ordered list
    if (/^\d+\. /.test(line)) {
      const items: React.ReactNode[] = [];
      while (i < normalizedLines.length && /^\d+\. /.test(normalizedLines[i])) {
        items.push(
          <li key={i} style={{ marginBottom: '0.3rem', color: '#374151', paddingLeft: '0.15rem' }}>
            {inlineFormat(normalizedLines[i].replace(/^\d+\. /, ''))}
          </li>
        );
        i++;
      }
      nodes.push(
        <ol key={`ol-${i}`} style={{ listStyleType: 'decimal', paddingLeft: '1.5rem', margin: '0.5rem 0 0.75rem' }}>
          {items}
        </ol>
      );
      continue;
    }

    // Plain paragraph — accumulate consecutive non-special lines
    const paraLines: string[] = [];
    while (
      i < normalizedLines.length &&
      normalizedLines[i].trim() !== '' &&
      !/^#{1,4} /.test(normalizedLines[i]) &&
      !/^[-*+] /.test(normalizedLines[i]) &&
      !/^\d+\. /.test(normalizedLines[i]) &&
      !/^> /.test(normalizedLines[i]) &&
      !/^---+$/.test(normalizedLines[i].trim())
    ) {
      paraLines.push(normalizedLines[i]);
      i++;
    }
    if (paraLines.length > 0) {
      nodes.push(
        <p key={`p-${i}`} style={{ marginBottom: '0.65rem', color: '#374151', lineHeight: 1.7 }}>
          {inlineFormat(paraLines.join(' '))}
        </p>
      );
    }
  }

  return nodes;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const rendered = parseMarkdown(content);
  return (
    <div style={{ fontFamily: "'Inter', ui-sans-serif, system-ui, sans-serif", fontSize: 14, lineHeight: 1.7, color: '#1f2937' }}>
      {rendered}
    </div>
  );
}
