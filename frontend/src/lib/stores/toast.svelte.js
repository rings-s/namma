/**
 * Global toast/notification store. Components push messages; the <Toaster/>
 * mounted in the root layout renders them. Auto-dismiss after a timeout.
 *
 * @typedef {'success' | 'error' | 'info'} ToastKind
 * @typedef {{ id: number; kind: ToastKind; message: string }} Toast
 */
function createToasts() {
	/** @type {Toast[]} */
	let items = $state([]);
	let seq = 0;

	/**
	 * @param {string} message
	 * @param {ToastKind} [kind]
	 * @param {number} [timeout]
	 */
	function push(message, kind = 'info', timeout = 4000) {
		const id = ++seq;
		items.push({ id, kind, message });
		if (timeout > 0) setTimeout(() => dismiss(id), timeout);
		return id;
	}

	/** @param {number} id */
	function dismiss(id) {
		items = items.filter((toast) => toast.id !== id);
	}

	return {
		get items() {
			return items;
		},
		push,
		dismiss,
		/** @param {string} m */
		success: (m) => push(m, 'success'),
		/** @param {string} m */
		error: (m) => push(m, 'error', 6000),
		/** @param {string} m */
		info: (m) => push(m, 'info')
	};
}

export const toasts = createToasts();
