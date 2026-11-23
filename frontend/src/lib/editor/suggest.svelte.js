// State for the @reference / #tag autocomplete popup.
//
// Tiptap's Suggestion plugin calls the lifecycle functions returned by
// `renderer()`; they copy what it reports into this $state object, and the
// <SuggestPopup> component (mounted once in the layout) draws it.

export const suggest = $state({
	open: false,
	kind: /** @type {'ref'|'tag'} */ ('ref'),
	items: /** @type {any[]} */ ([]),
	index: 0,
	rect: /** @type {DOMRect|null} */ (null),
	loading: false
});

/** @type {((item:any) => void) | null} */
let pick = null;

export function choose(i) {
	const item = suggest.items[i];
	if (item && pick) pick(item);
}

/** @param {'ref'|'tag'} kind */
export function renderer(kind) {
	return () => {
		const update = (props) => {
			suggest.kind = kind;
			suggest.items = props.items;
			suggest.rect = props.clientRect?.() ?? null;
			if (suggest.index >= props.items.length) suggest.index = 0;
			pick = (item) => props.command(item);
		};
		return {
			onStart(props) {
				suggest.open = true;
				suggest.index = 0;
				update(props);
			},
			onUpdate: update,
			onKeyDown({ event }) {
				if (!suggest.open || !suggest.items.length) return false;
				if (event.key === 'ArrowDown') {
					suggest.index = (suggest.index + 1) % suggest.items.length;
					return true;
				}
				if (event.key === 'ArrowUp') {
					suggest.index = (suggest.index - 1 + suggest.items.length) % suggest.items.length;
					return true;
				}
				if (event.key === 'Enter' || event.key === 'Tab') {
					choose(suggest.index);
					return true;
				}
				if (event.key === 'Escape') {
					suggest.open = false;
					return true;
				}
				return false;
			},
			onExit() {
				suggest.open = false;
				suggest.items = [];
				pick = null;
			}
		};
	};
}
