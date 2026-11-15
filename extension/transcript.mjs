// Convert the visible transcript into individual, correctly attributed messages.
// Unknown/unlabelled text defaults to inbound (customer) rather than salesperson.
export function parseTranscript(value) {
  const input = String(value ?? "").trim();
  if (!input) return [];

  const lines = input.split(/\\r?\\n/);
  const entries = [];
  let current = null;
  let sawSpeakerLabel = false;

  for (const line of lines) {
    const match = line.match(/^\\s*(Customer|Salesperson)\\s*:\\s?(.*)$/i);
    if (match) {
      sawSpeakerLabel = true;
      if (current && current.body.trim()) entries.push(current);
      current = {
        direction: match[1].toLowerCase() === "salesperson" ? "outbound" : "inbound",
        body: match[2],
      };
    } else if (current) {
      current.body += (current.body ? "\\n" : "") + line;
    } else if (line.trim()) {
      current = { direction: "inbound", body: line };
    }
  }

  if (current && current.body.trim()) entries.push(current);
  if (!sawSpeakerLabel) {
    const body = input;
    return body ? [{ direction: "inbound", body }] : [];
  }
  return entries.map(({ direction, body }) => ({ direction, body: body.trim() })).filter((entry) => entry.body);
}
