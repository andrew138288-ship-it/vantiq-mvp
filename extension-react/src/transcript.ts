export type TranscriptMessage = {
  direction: "inbound" | "outbound";
  body: string;
};

export function parseTranscript(value: string): TranscriptMessage[] {
  const messages: TranscriptMessage[] = [];
  let current: TranscriptMessage | null = null;

  for (const line of value.replace(/\r\n?/g, "\n").split("\n")) {
    const match = line.match(/^(Customer|Salesperson):\s*(.*)$/i);
    if (match) {
      if (current?.body.trim()) messages.push(current);
      current = {
        direction: match[1].toLowerCase() === "salesperson" ? "outbound" : "inbound",
        body: match[2],
      };
    } else if (current) {
      current.body += (current.body ? "\n" : "") + line;
    } else if (line.trim()) {
      current = { direction: "inbound", body: line };
    }
  }

  if (current?.body.trim()) messages.push(current);
  return messages.map((message) => ({ ...message, body: message.body.trim() }));
}
