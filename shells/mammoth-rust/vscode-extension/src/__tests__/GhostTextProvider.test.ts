import { GhostTextProvider } from '../GhostTextProvider';

jest.mock(
  'vscode',
  () => ({
    InlineCompletionList: class {
      items: any[];
      constructor(items: any[]) {
        this.items = items;
      }
    },
    InlineCompletionItem: class {
      insertText: string;
      constructor(text: string) {
        this.insertText = text;
      }
    },
  }),
  { virtual: true },
);

describe('GhostTextProvider', () => {
  test('returns empty list when no suggestion is set', () => {
    const provider = new GhostTextProvider();
    const result = provider.provideInlineCompletionItems(
      {} as any,
      {} as any,
      {} as any,
      {} as any,
    );
    expect((result as any).items).toHaveLength(0);
  });

  test('returns suggestion when set', () => {
    const provider = new GhostTextProvider();
    provider.setSuggestion('console.log("hello")');
    const result = provider.provideInlineCompletionItems(
      {} as any,
      {} as any,
      {} as any,
      {} as any,
    );
    expect((result as any).items).toHaveLength(1);
    expect((result as any).items[0].insertText).toBe('console.log("hello")');
  });

  test('clearSuggestion removes suggestion', () => {
    const provider = new GhostTextProvider();
    provider.setSuggestion('foo');
    provider.clearSuggestion();
    expect(provider.currentSuggestion).toBeUndefined();
    const result = provider.provideInlineCompletionItems(
      {} as any,
      {} as any,
      {} as any,
      {} as any,
    );
    expect((result as any).items).toHaveLength(0);
  });
});
