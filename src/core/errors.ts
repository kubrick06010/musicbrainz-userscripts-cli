export class MbToolError extends Error { constructor(message: string, public readonly code: number, public readonly cause?: unknown) { super(message); this.name = 'MbToolError'; } }
export const invalidInput = (message: string) => new MbToolError(message, 2);
export const networkError = (message: string, cause?: unknown) => new MbToolError(message, 3, cause);
export const providerError = (message: string, cause?: unknown) => new MbToolError(message, 4, cause);
export const musicBrainzError = (message: string, cause?: unknown) => new MbToolError(message, 5, cause);
