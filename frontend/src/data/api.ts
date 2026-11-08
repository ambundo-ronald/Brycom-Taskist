/**
 * Extract a human-readable error message from Frappe's error response.
 * Frappe returns `_server_messages` as a JSON-encoded array of JSON-encoded strings.
 */
function extractFrappeError(responseData: any, fallback: string): string {
	try {
		if (responseData?._server_messages) {
			const messages = JSON.parse(responseData._server_messages)
			const texts: string[] = []
			for (const msg of messages) {
				try {
					const parsed = JSON.parse(msg)
					const text = parsed.message || parsed.title || msg
					// Strip HTML tags
					texts.push(text.replace(/<[^>]+>/g, '').trim())
				} catch {
					texts.push(String(msg).replace(/<[^>]+>/g, '').trim())
				}
			}
			if (texts.length) return texts.join('\n')
		}
		if (responseData?.message) return responseData.message
		if (responseData?.exc) return responseData.exc
	} catch { /* fall through */ }
	return fallback
}

function isLoggedOut(): boolean {
	const m = document.cookie.match(/(?:^|;\s*)user_id=([^;]*)/)
	const user = m ? decodeURIComponent(m[1]) : ''
	return !user || user === 'Guest'
}

/**
 * Redirect to login only when the session has really ended.
 * A 403 for a logged-in user just means "no permission for this record"
 * (e.g. a technician reading Projects) and must not trigger a redirect,
 * otherwise login bounces straight back and the page reloads forever.
 */
function handleAuthError(res: Response): boolean {
	if (res.status === 401 || (res.status === 403 && isLoggedOut())) {
		window.location.href = '/login?redirect-to=' + encodeURIComponent(window.location.pathname)
		return true
	}
	return false
}

export async function call(method: string, args: Record<string, any> = {}): Promise<any> {
	const res = await fetch('/api/method/' + method, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'X-Frappe-CSRF-Token': getCSRFToken(),
		},
		body: JSON.stringify(args),
	})

	if (!res.ok) {
		if (handleAuthError(res)) return
		const error = await res.json().catch(() => ({ message: res.statusText }))
		throw new Error(extractFrappeError(error, 'API call failed'))
	}

	const data = await res.json()
	return data.message
}

export async function getList(
	doctype: string,
	params: {
		fields?: string[]
		filters?: Record<string, any>
		order_by?: string
		limit_page_length?: number
		limit_start?: number
	} = {}
): Promise<any[]> {
	const queryParams = new URLSearchParams()
	if (params.fields) queryParams.set('fields', JSON.stringify(params.fields))
	if (params.filters) queryParams.set('filters', JSON.stringify(params.filters))
	if (params.order_by) queryParams.set('order_by', params.order_by)
	if (params.limit_page_length) queryParams.set('limit_page_length', String(params.limit_page_length))
	if (params.limit_start) queryParams.set('limit_start', String(params.limit_start))

	const res = await fetch(`/api/resource/${doctype}?${queryParams.toString()}`, {
		headers: {
			'X-Frappe-CSRF-Token': getCSRFToken(),
		},
	})

	if (!res.ok) {
		if (handleAuthError(res)) return []
		const error = await res.json().catch(() => ({ message: res.statusText }))
		throw new Error(extractFrappeError(error, 'Failed to fetch list'))
	}

	const data = await res.json()
	return data.data
}

export async function getDoc(doctype: string, name: string): Promise<any> {
	const res = await fetch(`/api/resource/${doctype}/${encodeURIComponent(name)}`, {
		headers: {
			'X-Frappe-CSRF-Token': getCSRFToken(),
		},
	})

	if (!res.ok) {
		if (handleAuthError(res)) return null
		const error = await res.json().catch(() => ({ message: res.statusText }))
		throw new Error(extractFrappeError(error, 'Failed to fetch document'))
	}

	const data = await res.json()
	return data.data
}

export async function saveDoc(doc: any): Promise<any> {
	const res = await fetch(`/api/resource/${doc.doctype}/${encodeURIComponent(doc.name)}`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			'X-Frappe-CSRF-Token': getCSRFToken(),
		},
		body: JSON.stringify(doc),
	})

	if (!res.ok) {
		if (handleAuthError(res)) return null
		const error = await res.json().catch(() => ({ message: res.statusText }))
		throw new Error(extractFrappeError(error, 'Failed to save document'))
	}

	const data = await res.json()
	return data.data
}

export function getCSRFToken(): string {
	return (
		(window as any).csrf_token ||
		(document.cookie.match(/csrf_token=([^;]+)/) || ['', ''])[1]
	)
}
