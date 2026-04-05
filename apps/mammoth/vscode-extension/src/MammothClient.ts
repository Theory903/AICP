export interface MammothClientOptions {
  baseUrl: string;
  reconnectDelayMs?: number;
}

export type MessageHandler = (content: string) => void;
export type ApprovalHandler = (approvalId: string, capabilityName: string, description: string) => void;

export class MammothClient {
  private readonly baseUrl: string;
  private readonly reconnectDelayMs: number;
  private es: EventSource | null = null;
  private messageHandlers: MessageHandler[] = [];
  private approvalHandlers: ApprovalHandler[] = [];

  constructor(opts: MammothClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, '');
    this.reconnectDelayMs = opts.reconnectDelayMs ?? 3000;
  }

  connect(): void {
    if (this.es) {
      this.es.close();
    }
    this.es = new EventSource(`${this.baseUrl}/ext/events`);

    this.es.addEventListener('message', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data as string);
        if (payload.type === 'message' && typeof payload.content === 'string') {
          this.messageHandlers.forEach((h) => h(payload.content));
        }
      } catch {
        // Ignore malformed events
      }
    });

    this.es.addEventListener('approval_request', ((e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data as string);
        this.approvalHandlers.forEach((h) =>
          h(payload.approval_id, payload.capability_name, payload.description)
        );
      } catch {
        // Ignore malformed events
      }
    }) as unknown as (e: Event) => void);

    this.es.onerror = () => {
      this.es?.close();
      this.es = null;
      setTimeout(() => this.connect(), this.reconnectDelayMs);
    };
  }

  async sendMessage(text: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/ext/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });
    if (!response.ok) {
      throw new Error(`sendMessage failed: ${response.status}`);
    }
  }

  onMessage(handler: MessageHandler): void {
    this.messageHandlers.push(handler);
  }

  onApprovalRequest(handler: ApprovalHandler): void {
    this.approvalHandlers.push(handler);
  }

  disconnect(): void {
    this.es?.close();
    this.es = null;
  }
}
