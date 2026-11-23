// The four meaning-based highlight colors. Number keys 1–4 apply them.
export const HIGHLIGHTS = [
	{ id: 'promise', label: 'Promise', key: '1', color: 'var(--hl-promise)' },
	{ id: 'christ', label: 'Christ', key: '2', color: 'var(--hl-christ)' },
	{ id: 'doctrine', label: 'Doctrine', key: '3', color: 'var(--hl-doctrine)' },
	{ id: 'question', label: 'Question', key: '4', color: 'var(--hl-question)' }
];

export const byId = Object.fromEntries(HIGHLIGHTS.map((h) => [h.id, h]));
export const byKey = Object.fromEntries(HIGHLIGHTS.map((h) => [h.key, h]));
