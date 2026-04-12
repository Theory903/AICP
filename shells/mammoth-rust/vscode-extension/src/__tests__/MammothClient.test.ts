import { MammothClient, MammothClientOptions } from '../MammothClient';

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

class MockEventSource {
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  addEventListener = jest.fn();
  close = jest.fn();
  static instances: MockEventSource[] = [];
  constructor(public url: string) {
    MockEventSource.instances.push(this);
  }
}
(global as any).EventSource = MockEventSource;

describe('MammothClient', () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    mockFetch.mockReset();
  });

  test('connects to correct SSE endpoint', () => {
    const opts: MammothClientOptions = { baseUrl: 'http://localhost:3080' };
    const client = new MammothClient(opts);
    client.connect();
    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toBe('http://localhost:3080/ext/events');
  });

  test('sendMessage posts to /ext/message', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });
    const opts: MammothClientOptions = { baseUrl: 'http://localhost:3080' };
    const client = new MammothClient(opts);
    await client.sendMessage('hello');
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:3080/ext/message',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ message: 'hello' }),
      })
    );
  });

  test('onMessage callback is invoked for message events', () => {
    const opts: MammothClientOptions = { baseUrl: 'http://localhost:3080' };
    const received: string[] = [];
    const client = new MammothClient(opts);
    client.onMessage((content) => received.push(content));
    client.connect();
    const es = MockEventSource.instances[0];
    const [, handler] = (es.addEventListener as jest.Mock).mock.calls.find(
      ([name]: [string]) => name === 'message'
    );
    handler({ data: JSON.stringify({ type: 'message', content: 'hi there' }) });
    expect(received).toEqual(['hi there']);
  });
});
