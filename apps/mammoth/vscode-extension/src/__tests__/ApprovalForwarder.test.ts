import { ApprovalForwarder } from '../ApprovalForwarder';

const mockShowInformationMessage = jest.fn();
jest.mock(
  'vscode',
  () => ({
    window: { showInformationMessage: (...args: any[]) => mockShowInformationMessage(...args) },
  }),
  { virtual: true },
);

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

describe('ApprovalForwarder', () => {
  beforeEach(() => {
    mockShowInformationMessage.mockReset();
    mockFetch.mockReset();
    mockFetch.mockResolvedValue({ ok: true });
  });

  test('returns true when user clicks Approve', async () => {
    mockShowInformationMessage.mockResolvedValueOnce('Approve');
    const fwd = new ApprovalForwarder({ baseUrl: 'http://localhost:3080' });
    const result = await fwd.promptApproval('appr_1', 'payments.transfer', 'Send $50');
    expect(result).toBe(true);
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:3080/ext/approval',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ approval_id: 'appr_1', approved: true, decided_by: 'vscode' }),
      }),
    );
  });

  test('returns false when user clicks Deny', async () => {
    mockShowInformationMessage.mockResolvedValueOnce('Deny');
    const fwd = new ApprovalForwarder({ baseUrl: 'http://localhost:3080' });
    const result = await fwd.promptApproval('appr_2', 'admin.delete', 'Delete all');
    expect(result).toBe(false);
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:3080/ext/approval',
      expect.objectContaining({
        body: JSON.stringify({ approval_id: 'appr_2', approved: false, decided_by: 'vscode' }),
      }),
    );
  });

  test('returns false when user dismisses the notification', async () => {
    mockShowInformationMessage.mockResolvedValueOnce(undefined);
    const fwd = new ApprovalForwarder({ baseUrl: 'http://localhost:3080' });
    const result = await fwd.promptApproval('appr_3', 'notes.create', 'Create note');
    expect(result).toBe(false);
  });
});
