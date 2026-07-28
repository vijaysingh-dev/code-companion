// Minimal, CSP-safe Markdown → HTML renderer for assistant messages. The webview
// CSP forbids external libraries, so this covers the subset models actually emit:
// headings, bold/italic, inline + fenced code (with diff highlighting), lists,
// blockquotes, links, and paragraphs. All raw text is HTML-escaped before it ever
// reaches innerHTML, and only a fixed set of tags / link schemes is emitted.

const ESCAPE = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" };
const escapeHtml = (s) => s.replace(/[&<>"]/g, (c) => ESCAPE[c]);

// Only http(s)/mailto/file/vscode/anchor links are allowed; anything else stays plain text.
const safeHref = (url) => (/^(https?:|mailto:|file:|vscode:|#)/i.test(url.trim()) ? url.trim() : null);

const isBlockStart = (line) =>
  /^```/.test(line) ||
  /^#{1,6}\s+/.test(line) ||
  /^>\s?/.test(line) ||
  /^\s*([-*+]|\d+\.)\s+/.test(line) ||
  /^\s*([-*_])(\s*\1){2,}\s*$/.test(line);

// Inline spans. Inline code is pulled out of the raw text first so its contents
// aren't escaped twice or reformatted, then spliced back in at the end.
function inline(text) {
  const codes = [];
  let s = text.replace(/`([^`]+)`/g, (_, code) => {
    codes.push(code);
    return `\u0000${codes.length - 1}\u0000`;
  });
  s = escapeHtml(s)
    .replace(/\*\*([^*]+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__([^_]+?)__/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*]+?)\*/g, "$1<em>$2</em>")
    .replace(/(^|[^_\w])_([^_]+?)_/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, label, url) => {
      const href = safeHref(url);
      return href ? `<a href="${escapeHtml(href)}">${label}</a>` : m;
    });
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${escapeHtml(codes[i])}</code>`);
}

function codeBlock(lang, code) {
  if (lang === "diff") {
    const rows = code.split("\n").map((ln) => {
      const cls = /^(diff |index |@@|\+\+\+|---)/.test(ln)
        ? "meta"
        : ln[0] === "+"
          ? "add"
          : ln[0] === "-"
            ? "del"
            : "ctx";
      return `<span class="cc-diff-${cls}">${escapeHtml(ln) || " "}</span>`;
    });
    return `<pre class="cc-code cc-diff"><code>${rows.join("\n")}</code></pre>`;
  }
  const cls = lang ? ` class="language-${escapeHtml(lang)}"` : "";
  return `<pre class="cc-code"><code${cls}>${escapeHtml(code)}</code></pre>`;
}

export function renderMarkdown(src) {
  const lines = src.replace(/\r\n/g, "\n").split("\n");
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    const fence = line.match(/^```(\w*)/);
    if (fence) {
      const buf = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) {
        buf.push(lines[i]);
        i++;
      }
      i++; // skip the closing fence (or fall off the end while still streaming)
      out.push(codeBlock(fence[1], buf.join("\n")));
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      out.push(`<h${heading[1].length}>${inline(heading[2])}</h${heading[1].length}>`);
      i++;
      continue;
    }

    if (/^>\s?/.test(line)) {
      const buf = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) {
        buf.push(lines[i].replace(/^>\s?/, ""));
        i++;
      }
      out.push(`<blockquote>${renderMarkdown(buf.join("\n"))}</blockquote>`);
      continue;
    }

    if (/^\s*([-*+]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\.\s+/.test(line);
      const items = [];
      while (i < lines.length && /^\s*([-*+]|\d+\.)\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*([-*+]|\d+\.)\s+/, ""));
        i++;
      }
      const tag = ordered ? "ol" : "ul";
      out.push(`<${tag}>${items.map((it) => `<li>${inline(it)}</li>`).join("")}</${tag}>`);
      continue;
    }

    if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) {
      out.push("<hr>");
      i++;
      continue;
    }

    if (line.trim() === "") {
      i++;
      continue;
    }

    const buf = [line];
    i++;
    while (i < lines.length && lines[i].trim() !== "" && !isBlockStart(lines[i])) {
      buf.push(lines[i]);
      i++;
    }
    out.push(`<p>${inline(buf.join("\n")).replace(/\n/g, "<br>")}</p>`);
  }
  return out.join("\n");
}
