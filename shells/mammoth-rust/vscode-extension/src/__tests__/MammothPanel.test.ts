import { MammothPanel } from '../MammothPanel';

const mockPanel = {
  webview: {
    html: '',
    onDidReceiveMessage: jest.fn(),
    postMessage: jest.fn(),
  },
  onDidDispose: jest.fn(),
  reveal: jest.fn(),
  dispose: jest.fn(),
};
const mockCreateWebviewPanel = jest.fn(() => mockPanel);
jest.mock(
  'vscode',
  () => ({
    window: { createWebviewPanel: function() { return mockCreateWebviewPanel.apply(null, arguments); } },
    ViewColumn: { One: 1 },
  }),
  { virtual: true },
);

describe('MammothPanel', () => {
  beforeEach(() => {
    MammothPanel.currentPanel = undefined;
    mockCreateWebviewPanel.mockClear();
    mockPanel.webview.postMessage.mockClear();
  });

  test('createOrShow creates a new panel on first call', () => {
    MammothPanel.createOrShow({ extensionUri: { fsPath: '/ext' } as any } as any);
    expect(mockCreateWebviewPanel).toHaveBeenCalledTimes(1);
    expect(mockCreateWebviewPanel).toHaveBeenCalledWith(
      'mammothPanel',
      'Mammoth',
      1,
      expect.objectContaining({ enableScripts: true }),
    );
  });

  test('postMessage sends content to webview', () => {
    const panel = new MammothPanel(mockPanel as any);
    panel.addMessage('assistant', 'Hello from Mammoth');
    expect(mockPanel.webview.postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'message', role: 'assistant', content: 'Hello from Mammoth' }),
    );
  });
});
