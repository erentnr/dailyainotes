/** Server-sent events from POST /api/v1/ask, read with fetch: EventSource cannot POST. */

export interface ServerEvent {
  event: string;
  data: unknown;
}

/** Complete events in `buffer`, and the unfinished rest to keep for the next chunk. */
export function parseEvents(buffer: string): { events: ServerEvent[]; rest: string } {
  const blocks = buffer.split("\n\n");
  const rest = blocks.pop() ?? "";
  const events = blocks.flatMap((block) => {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event: ")) event = line.slice(7);
      else if (line.startsWith("data: ")) data.push(line.slice(6));
    }
    return data.length ? [{ event, data: JSON.parse(data.join("\n")) as unknown }] : [];
  });
  return { events, rest };
}

export async function* readEvents(response: Response): AsyncGenerator<ServerEvent> {
  if (!response.body) return;
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    const parsed = parseEvents(buffer + value);
    buffer = parsed.rest;
    yield* parsed.events;
  }
}
