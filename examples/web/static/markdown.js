(function attachMarkdownRenderer(global) {
  "use strict";

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replaceAll("`", "&#96;");
  }

  function sanitizeUrl(value) {
    const trimmed = String(value || "").trim();
    if (!trimmed) {
      return "#";
    }

    const hasProtocol = /^[a-zA-Z][a-zA-Z\d+.-]*:/.test(trimmed);
    if (hasProtocol && !/^(https?:|mailto:)/i.test(trimmed)) {
      return "#";
    }

    return escapeAttribute(trimmed);
  }

  function renderInline(markdown) {
    const tokens = [];
    const pushToken = (html) => {
      const token = `\u0000MD${tokens.length}\u0000`;
      tokens.push(html);
      return token;
    };

    let text = String(markdown || "");

    text = text.replace(/`([^`\n]+)`/g, (_match, code) =>
      pushToken(`<code>${escapeHtml(code)}</code>`),
    );

    text = text.replace(/\[([^\]\n]+)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g, (_match, label, url) =>
      pushToken(
        `<a href="${sanitizeUrl(url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`,
      ),
    );

    text = escapeHtml(text);
    text = text.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/__([^_\n]+)__/g, "<strong>$1</strong>");
    text = text.replace(/~~([^~\n]+)~~/g, "<del>$1</del>");
    text = text.replace(/(^|[^\*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
    text = text.replace(/(^|[^_])_([^_\n]+)_/g, "$1<em>$2</em>");

    tokens.forEach((html, index) => {
      text = text.replaceAll(`\u0000MD${index}\u0000`, html);
    });

    return text;
  }

  function isBlank(line) {
    return /^\s*$/.test(line);
  }

  function isFenceStart(line) {
    return /^\s*```/.test(line);
  }

  function isHeading(line) {
    return /^(#{1,4})\s+/.test(line);
  }

  function isHorizontalRule(line) {
    return /^\s*([-*_])(?:\s*\1){2,}\s*$/.test(line);
  }

  function isBlockquote(line) {
    return /^\s*>\s?/.test(line);
  }

  function isUnorderedList(line) {
    return /^\s*[-*+]\s+/.test(line);
  }

  function isOrderedList(line) {
    return /^\s*\d+[.)]\s+/.test(line);
  }

  function isTableSeparator(line) {
    return /^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/.test(line);
  }

  function isTableStart(lines, index) {
    return (
      index + 1 < lines.length &&
      lines[index].includes("|") &&
      isTableSeparator(lines[index + 1])
    );
  }

  function isBlockStart(lines, index) {
    const line = lines[index] || "";
    return (
      isFenceStart(line) ||
      isHeading(line) ||
      isHorizontalRule(line) ||
      isBlockquote(line) ||
      isUnorderedList(line) ||
      isOrderedList(line) ||
      isTableStart(lines, index)
    );
  }

  function renderCodeBlock(lines, startIndex) {
    const firstLine = lines[startIndex];
    const language = firstLine.replace(/^\s*```/, "").trim().split(/\s+/)[0] || "";
    const codeLines = [];
    let index = startIndex + 1;

    while (index < lines.length && !isFenceStart(lines[index])) {
      codeLines.push(lines[index]);
      index += 1;
    }

    if (index < lines.length) {
      index += 1;
    }

    const className = language ? ` class="language-${escapeAttribute(language)}"` : "";
    return {
      html: `<pre><code${className}>${escapeHtml(codeLines.join("\n"))}</code></pre>`,
      nextIndex: index,
    };
  }

  function splitTableRow(line) {
    return line
      .trim()
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((cell) => cell.trim());
  }

  function renderTable(lines, startIndex) {
    const headers = splitTableRow(lines[startIndex]);
    const rows = [];
    let index = startIndex + 2;

    while (index < lines.length && lines[index].includes("|") && !isBlank(lines[index])) {
      rows.push(splitTableRow(lines[index]));
      index += 1;
    }

    const head = headers.map((header) => `<th>${renderInline(header)}</th>`).join("");
    const body = rows
      .map((row) => {
        const cells = headers.map((_header, cellIndex) => row[cellIndex] || "");
        return `<tr>${cells.map((cell) => `<td>${renderInline(cell)}</td>`).join("")}</tr>`;
      })
      .join("");

    return {
      html: `<div class="markdown-table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`,
      nextIndex: index,
    };
  }

  function renderList(lines, startIndex, ordered) {
    const tag = ordered ? "ol" : "ul";
    const items = [];
    let index = startIndex;
    const matcher = ordered ? /^\s*\d+[.)]\s+/ : /^\s*[-*+]\s+/;

    while (index < lines.length && matcher.test(lines[index])) {
      items.push(lines[index].replace(matcher, ""));
      index += 1;
    }

    return {
      html: `<${tag}>${items.map((item) => `<li>${renderInline(item)}</li>`).join("")}</${tag}>`,
      nextIndex: index,
    };
  }

  function renderBlockquote(lines, startIndex) {
    const quoteLines = [];
    let index = startIndex;

    while (index < lines.length && isBlockquote(lines[index])) {
      quoteLines.push(lines[index].replace(/^\s*>\s?/, ""));
      index += 1;
    }

    return {
      html: `<blockquote><p>${quoteLines.map(renderInline).join("<br>")}</p></blockquote>`,
      nextIndex: index,
    };
  }

  function renderParagraph(lines, startIndex) {
    const paragraphLines = [];
    let index = startIndex;

    while (index < lines.length && !isBlank(lines[index]) && !isBlockStart(lines, index)) {
      paragraphLines.push(lines[index]);
      index += 1;
    }

    return {
      html: `<p>${paragraphLines.map(renderInline).join("<br>")}</p>`,
      nextIndex: index,
    };
  }

  function renderMarkdown(markdown) {
    const source = String(markdown || "").replace(/\r\n?/g, "\n").trim();
    if (!source) {
      return "";
    }

    const lines = source.split("\n");
    const blocks = [];
    let index = 0;

    while (index < lines.length) {
      const line = lines[index];

      if (isBlank(line)) {
        index += 1;
        continue;
      }

      if (isFenceStart(line)) {
        const result = renderCodeBlock(lines, index);
        blocks.push(result.html);
        index = result.nextIndex;
        continue;
      }

      if (isTableStart(lines, index)) {
        const result = renderTable(lines, index);
        blocks.push(result.html);
        index = result.nextIndex;
        continue;
      }

      const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
      if (headingMatch) {
        const level = headingMatch[1].length + 2;
        blocks.push(`<h${level}>${renderInline(headingMatch[2])}</h${level}>`);
        index += 1;
        continue;
      }

      if (isHorizontalRule(line)) {
        blocks.push("<hr>");
        index += 1;
        continue;
      }

      if (isBlockquote(line)) {
        const result = renderBlockquote(lines, index);
        blocks.push(result.html);
        index = result.nextIndex;
        continue;
      }

      if (isUnorderedList(line)) {
        const result = renderList(lines, index, false);
        blocks.push(result.html);
        index = result.nextIndex;
        continue;
      }

      if (isOrderedList(line)) {
        const result = renderList(lines, index, true);
        blocks.push(result.html);
        index = result.nextIndex;
        continue;
      }

      const result = renderParagraph(lines, index);
      blocks.push(result.html);
      index = result.nextIndex;
    }

    return blocks.join("");
  }

  global.WenjiaMarkdown = {
    escapeHtml,
    renderMarkdown,
  };
})(typeof window !== "undefined" ? window : globalThis);
