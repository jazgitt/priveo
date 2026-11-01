import type { ReactNode } from "react";

/** The small part of Markdown a model reply uses: paragraphs, bullet and numbered lists, **bold** and `code`.
 *  Built as React elements, never as HTML, so text from the model cannot add markup. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) return <code key={i}>{part.slice(1, -1)}</code>;
    return part;
  });
}

const BULLET = /^\s*[*-]\s+(.*)$/;
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/;

export function RichText({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let paragraph: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  const flush = () => {
    if (paragraph.length) {
      blocks.push(<p key={blocks.length} className="m-0 break-words text-sm">{inline(paragraph.join(" "))}</p>);
      paragraph = [];
    }
    if (list) {
      const Tag = list.ordered ? "ol" : "ul";
      blocks.push(
        <Tag key={blocks.length} className={`m-0 flex flex-col gap-1 pl-5 text-sm ${list.ordered ? "list-decimal" : "list-disc"}`}>
          {list.items.map((item, i) => <li key={i} className="break-words">{inline(item)}</li>)}
        </Tag>,
      );
      list = null;
    }
  };
  for (const line of text.split("\n")) {
    const bullet = BULLET.exec(line);
    const numbered = bullet ? null : NUMBERED.exec(line);
    const item = bullet?.[1] ?? numbered?.[1];
    if (item !== undefined) {
      const ordered = Boolean(numbered);
      if (paragraph.length || (list && list.ordered !== ordered)) flush();
      list = list ?? { ordered, items: [] };
      list.items.push(item);
    } else if (!line.trim()) {
      flush();
    } else {
      if (list) flush();
      paragraph.push(line.trim());
    }
  }
  flush();
  return <div className="flex flex-col gap-2">{blocks}</div>;
}
