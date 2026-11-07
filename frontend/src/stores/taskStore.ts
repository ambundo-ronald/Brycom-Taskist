import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { call } from '@/data/api'

export interface Task {
	name: string
	subject: string
	status: string
	priority: string
	project: string
	parent_task: string
	// Dates - YYYY-MM-DD or YYYY-MM-DD HH:MM:SS when time is set
	exp_start_date: string | null
	exp_end_date: string | null
	expected_time: number
	progress: number
	// Native Task fields
	color: string | null
	is_group: boolean
	is_milestone: boolean
	type: string | null
	task_weight: number
	completed_by: string | null
	completed_on: string | null
	description: string | null
	act_start_date: string | null
	act_end_date: string | null
	actual_time: number
	total_costing_amount: number
	total_billing_amount: number
	// Taskist custom fields
	taskist_sort_order: number
	taskist_is_recurring: boolean
	taskist_recurrence_rule: string | null
	// Brycom installation job link (only on sites that have it)
	custom_installation_job?: string | null
	// Virtual / internal fields
	_assign: string
	_user_tags: string
	_last_comment: string | null
	_last_comment_at: string | null
	modified: string
	creation: string
}

/** The Task statuses used as kanban columns */
export const KANBAN_STATUSES = ['Open', 'Working', 'Pending Review', 'Overdue', 'Completed'] as const

export const useTaskStore = defineStore('tasks', () => {
	const tasks = ref<Task[]>([])
	const loading = ref(false)
	const selectedTask = ref<Task | null>(null)
	const showDetail = ref(false)
	const filters = ref<Record<string, any>>({})
	const searchQuery = ref('')
	const collapsedGroups = ref<Set<string>>(new Set())
	const nameSort = ref<'none' | 'asc' | 'desc'>('none')
	const groupFilter = ref<string | null>(null)

	function toggleNameSort() {
		if (nameSort.value === 'none') nameSort.value = 'asc'
		else if (nameSort.value === 'asc') nameSort.value = 'desc'
		else nameSort.value = 'none'
	}

	function toggleCollapse(taskName: string) {
		if (collapsedGroups.value.has(taskName)) {
			collapsedGroups.value.delete(taskName)
		} else {
			collapsedGroups.value.add(taskName)
		}
		// Trigger reactivity by replacing the Set
		collapsedGroups.value = new Set(collapsedGroups.value)
	}

	function isCollapsed(taskName: string) {
		return collapsedGroups.value.has(taskName)
	}

	function collapseAllGroups() {
		const groupNames = tasks.value
			.filter(t => childrenMap.value[t.name]?.length)
			.map(t => t.name)
		collapsedGroups.value = new Set(groupNames)
	}

	function expandAllGroups() {
		collapsedGroups.value = new Set()
	}

	const allCollapsed = computed(() => {
		const groupNames = tasks.value.filter(t => childrenMap.value[t.name]?.length)
		return groupNames.length > 0 && groupNames.every(t => collapsedGroups.value.has(t.name))
	})

	const filteredTasks = computed(() => {
		let result = tasks.value
		if (searchQuery.value) {
			const q = searchQuery.value.toLowerCase()
			result = result.filter(t => t.subject.toLowerCase().includes(q))
		}
		if (groupFilter.value) {
			const parentName = groupFilter.value
			result = result.filter(t => t.name === parentName || t.parent_task === parentName)
		}
		return result
	})

	/** Group tasks by status for kanban view */
	const tasksByStatus = computed(() => {
		const columns: Record<string, Task[]> = {}
		for (const status of KANBAN_STATUSES) {
			columns[status] = []
		}
		for (const task of filteredTasks.value) {
			const status = task.status || 'Open'
			if (columns[status]) {
				columns[status].push(task)
			} else {
				// Tasks with statuses not in KANBAN_STATUSES (e.g. Cancelled, Template) go to Open
				columns['Open'].push(task)
			}
		}
		for (const col of Object.keys(columns)) {
			columns[col].sort((a, b) => (a.taskist_sort_order || 0) - (b.taskist_sort_order || 0))
		}
		return columns
	})

	/** Map of parent_task name → child task names */
	const childrenMap = computed(() => {
		const map: Record<string, Task[]> = {}
		for (const task of tasks.value) {
			if (task.parent_task) {
				if (!map[task.parent_task]) map[task.parent_task] = []
				map[task.parent_task].push(task)
			}
		}
		return map
	})

	/** Build hierarchical task list: root tasks first, children indented below their parent */
	const hierarchicalTasks = computed(() => {
		const ft = filteredTasks.value
		const rootTasks = ft.filter(t => !t.parent_task || !ft.some(p => p.name === t.parent_task))
		const result: Array<Task & { _depth: number; _childCount: number }> = []

		function addWithChildren(task: Task, depth: number) {
			const children = childrenMap.value[task.name] || []
			const visibleChildren = children.filter(c => ft.includes(c))
			result.push({ ...task, _depth: depth, _childCount: visibleChildren.length })
			for (const child of visibleChildren) {
				addWithChildren(child, depth + 1)
			}
		}

		for (const task of rootTasks) {
			addWithChildren(task, 0)
		}
		return result
	})

	async function fetchTasks(extraFilters: Record<string, any> = {}) {
		loading.value = true
		try {
			const result = await call('taskist.api.get_tasks', {
				filters: { ...filters.value, ...extraFilters },
				include_completed: 1,
				page_length: 0,
			})
			tasks.value = result || []
		} catch (e) {
			console.error('Failed to fetch tasks:', e)
		} finally {
			loading.value = false
		}
	}

	async function quickCreate(data: {
		subject: string
		project?: string
		priority?: string
		status?: string
		parent_task?: string
		exp_start_date?: string
		exp_end_date?: string
	}) {
		const result = await call('taskist.api.quick_create_task', data)
		await fetchTasks()
		// Open the newly created task in the detail panel
		if (result && result.name) {
			const newTask = tasks.value.find(t => t.name === result.name)
			if (newTask) {
				selectTask(newTask)
			}
		}
		return result
	}

	async function updateTaskStatus(taskName: string, status: string, sortOrder?: number) {
		await call('taskist.api.update_task_status', {
			task_name: taskName,
			status,
			sort_order: sortOrder,
		})
	}

	function selectTask(task: Task | null) {
		selectedTask.value = task
		showDetail.value = !!task
	}

	function closeDetail() {
		selectedTask.value = null
		showDetail.value = false
	}

	function toggleGroupFilter(taskName: string) {
		groupFilter.value = groupFilter.value === taskName ? null : taskName
	}

	/** Move a group task and specific children to newStatus */
	async function moveGroupWithChildren(taskName: string, childNames: string[], newStatus: string, sortOrder?: number) {
		// Update parent
		await updateTaskStatus(taskName, newStatus, sortOrder)

		// Update children in parallel
		await Promise.all(
			childNames.map(name => updateTaskStatus(name, newStatus))
		)
	}

	return {
		tasks, loading, selectedTask, showDetail, filters, searchQuery,
		collapsedGroups, allCollapsed, nameSort, groupFilter,
		filteredTasks, tasksByStatus, childrenMap, hierarchicalTasks,
		fetchTasks, quickCreate, updateTaskStatus, selectTask, closeDetail,
		toggleCollapse, isCollapsed, collapseAllGroups, expandAllGroups, toggleNameSort,
		toggleGroupFilter, moveGroupWithChildren,
	}
})
