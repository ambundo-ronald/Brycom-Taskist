<template>
	<transition name="slide">
		<div
			v-if="taskStore.showDetail && taskStore.selectedTask"
			class="fixed right-0 top-0 h-full w-full sm:w-[480px] bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 shadow-xl z-40 flex flex-col"
		>
			<div class="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center gap-1.5 min-w-0">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">Task Details</h2>
					<a
						v-if="taskStore.selectedTask?.name"
						:href="`/desk/task/${taskStore.selectedTask.name}`"
						target="_blank"
						class="text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 flex-shrink-0"
						title="Open in Desk"
					>
						<FeatherIcon name="external-link" class="w-4 h-4" />
					</a>
				</div>
				<div class="flex items-center gap-2">
					<Button
						v-if="!isInstallation"
						@click="markCompleted"
						size="sm"
						:variant="isCompleted ? 'subtle' : 'ghost'"
						:theme="isCompleted ? 'green' : 'gray'"
						:label="isCompleted ? 'Completed' : 'Mark Completed'"
					/>
					<Button
						@click="taskStore.closeDetail()"
						size="sm"
						variant="ghost"
						label="Close"
					/>
				</div>
			</div>

			<div v-if="doc" class="flex-1 overflow-auto px-3 sm:px-4 py-3 space-y-3">
				<!-- Save error banner -->
				<div v-if="saveError" class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded px-3 py-2 text-xs text-red-700 dark:text-red-300 flex items-start gap-2">
					<FeatherIcon name="alert-circle" class="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
					<div class="flex-1 whitespace-pre-line">{{ saveError }}</div>
					<button @click="saveError = ''" class="text-red-400 hover:text-red-600 flex-shrink-0">
						<FeatherIcon name="x" class="w-3.5 h-3.5" />
					</button>
				</div>

				<!-- Subject -->
				<TextInput v-model="doc.subject" @blur="save" class="w-full text-sm font-medium" />

				<!-- Brycom installation job (receipt, vehicle details, mark installed) -->
				<InstallationPanel v-if="isInstallation" :task-name="doc.name" @changed="onInstallationChanged" />

				<!-- Status + Priority row -->
				<div class="grid grid-cols-2 gap-2">
					<div>
						<label class="block text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-0.5">Status</label>
						<FrappeSelect
							v-model="doc.status"
							@update:modelValue="save"
							:options="['Open', 'Working', 'Pending Review', 'Overdue', 'Completed', 'Cancelled']"
							class="w-full"
						/>
					</div>
					<div>
						<label class="block text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-0.5">Priority</label>
						<PrioritySlider v-model="doc.priority" @update:modelValue="save" />
					</div>
				</div>

				<!-- Type + Project row -->
				<div class="grid grid-cols-2 gap-2">
					<div>
						<label class="block text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-0.5">Type</label>
						<LinkField
							:model-value="doc.type || ''"
							@update:model-value="(v: string) => { doc.type = v; save() }"
							placeholder="Bug, Feature..."
							search-method="taskist.api.search_task_types"
							create-method="taskist.api.create_task_type"
							:allow-create="true"
						/>
					</div>
					<div>
						<label class="block text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-0.5">Project</label>
						<LinkField
							:model-value="doc.project || ''"
							@update:model-value="(v: string) => { doc.project = v; save() }"
							placeholder="Select project..."
							search-method="taskist.api.search_projects"
						/>
					</div>
				</div>

				<!-- Dates row -->
				<div class="grid grid-cols-2 gap-2">
					<div>
						<label class="block text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-0.5">Start</label>
						<DatetimePicker
							:model-value="doc.exp_start_date || ''"
							@update:model-value="(v: string) => { doc.exp_start_date = v; debouncedSave() }"
							placeholder="Start date/time"
							input-class="w-full border border-gray-200 dark:border-gray-600 rounded px-2 py-1 text-xs bg-white dark:bg-gray-700 dark:text-gray-200"
						/>
					</div>
					<div>
						<label class="block text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-0.5">End</label>
						<DatetimePicker
							:model-value="doc.exp_end_date || ''"
							@update:model-value="(v: string) => { doc.exp_end_date = v; debouncedSave() }"
							placeholder="End date/time"
							input-class="w-full border border-gray-200 dark:border-gray-600 rounded px-2 py-1 text-xs bg-white dark:bg-gray-700 dark:text-gray-200"
						/>
					</div>
				</div>

				<!-- Hours + Progress row -->
				<div class="grid grid-cols-3 gap-2">
					<div>
						<label class="block text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-0.5">Est. Hrs</label>
						<input v-model.number="doc.expected_time" @change="save" type="number" min="0" step="0.5" class="w-full border border-gray-200 dark:border-gray-600 rounded px-2 py-1 text-xs bg-white dark:bg-gray-700 dark:text-gray-200" />
					</div>
					<div>
						<label class="block text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-0.5">Actual</label>
						<input :value="doc.actual_time || 0" disabled class="w-full border border-gray-200 dark:border-gray-600 rounded px-2 py-1 text-xs bg-gray-50 dark:bg-gray-700/50 dark:text-gray-400 cursor-not-allowed" />
					</div>
					<div>
						<label class="block text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-0.5">{{ doc.progress || 0 }}%</label>
						<input v-model.number="doc.progress" @change="save" type="range" min="0" max="100" step="10" class="w-full mt-1" />
					</div>
				</div>

				<!-- Color, Flags & Recurrence inline -->
				<div class="flex items-center gap-3 flex-wrap">
					<div class="flex items-center gap-1.5">
						<input v-model="doc.color" @change="save" type="color" class="w-5 h-5 rounded border border-gray-200 dark:border-gray-600 cursor-pointer bg-transparent" />
						<button v-if="doc.color" @click="doc.color = ''; save()" class="text-[10px] text-gray-400 hover:text-red-500">clear</button>
					</div>
					<FrappeCheckbox
						:model-value="!!doc.is_milestone"
						@update:model-value="(v: boolean) => { doc.is_milestone = v ? 1 : 0; save() }"
						label="Milestone"
					/>
					<FrappeCheckbox
						:model-value="!!doc.is_group"
						@update:model-value="(v: boolean) => { doc.is_group = v ? 1 : 0; save() }"
						label="Group"
					/>
					<RecurrenceEditor
						:model-value="doc.taskist_recurrence_rule || ''"
						:is-recurring="!!doc.taskist_is_recurring"
						@update:model-value="(v: string) => { doc.taskist_recurrence_rule = v; save() }"
						@update:is-recurring="(v: boolean) => { doc.taskist_is_recurring = v ? 1 : 0; save() }"
					/>
				</div>

				<!-- Description -->
				<div>
					<label class="block text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-0.5">Description</label>
					<FrappeTextarea v-model="doc.description" @blur="save" :rows="2" placeholder="Add a description..." />
				</div>

				<!-- Assignees -->
				<div>
					<label class="block text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-1">
						Assigned To
						<button @click="assignToMe" class="ml-1 text-blue-500 hover:text-blue-700 dark:hover:text-blue-300 hover:underline">(assign to me)</button>
					</label>
					<div v-if="assignees.length" class="flex flex-wrap gap-1 mb-1.5">
						<div
							v-for="assignee in assignees"
							:key="assignee.email"
							class="flex items-center gap-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full pl-1 pr-0.5 py-0.5 text-[11px]"
						>
							<Avatar :label="assignee.full_name" size="xs" />
							<span class="px-1">{{ assignee.full_name }}</span>
							<button @click="removeAssignee(assignee.email)" class="p-0.5 rounded-full hover:bg-blue-200 dark:hover:bg-blue-800">
								<FeatherIcon name="x" class="w-2.5 h-2.5" />
							</button>
						</div>
					</div>
					<div class="relative">
						<input
							v-model="userSearch"
							@input="searchUsers"
							@focus="showUserDropdown = true"
							type="text"
							placeholder="Search users..."
							class="w-full border border-gray-200 dark:border-gray-600 rounded px-2.5 py-1 text-xs bg-white dark:bg-gray-700 dark:text-gray-200 dark:placeholder-gray-400"
						/>
						<div
							v-if="showUserDropdown && userResults.length"
							class="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg z-10 max-h-32 overflow-auto"
						>
							<button
								v-for="user in userResults"
								:key="user.name"
								@mousedown.prevent="addAssignee(user.name)"
								class="w-full text-left px-2.5 py-1.5 text-xs hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-200 flex items-center gap-2"
							>
								<Avatar :label="user.full_name || user.name" size="xs" />
								<div class="truncate">
									<span class="font-medium">{{ user.full_name || user.name }}</span>
									<span v-if="user.full_name" class="text-gray-400 dark:text-gray-500 ml-1">{{ user.name }}</span>
								</div>
							</button>
						</div>
					</div>
				</div>

				<!-- Attachments -->
				<TaskAttachments v-if="doc.name" :task-name="doc.name" />

				<!-- Parent Task -->
				<div v-if="doc.parent_task" class="flex items-center gap-1.5 px-2 py-1.5 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
					<FeatherIcon name="corner-up-left" class="w-3.5 h-3.5 text-purple-500 flex-shrink-0" />
					<span class="text-[11px] text-gray-500 dark:text-gray-400">Parent:</span>
					<button
						@click="taskStore.selectTask({ name: doc.parent_task } as any)"
						class="text-[11px] font-medium text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300 hover:underline truncate"
					>
						{{ doc.parent_task }}
					</button>
				</div>

				<!-- Subtasks -->
				<div>
					<div class="flex items-center justify-between mb-1">
						<h3 class="text-[11px] font-medium text-gray-400 dark:text-gray-500">Subtasks</h3>
						<button @click="showSubtaskAdd = true" class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400" title="Add subtask">
							<FeatherIcon name="plus" class="w-3.5 h-3.5" />
						</button>
					</div>
					<div v-if="showSubtaskAdd" class="mb-1.5 flex gap-1.5">
						<input
							ref="subtaskInput"
							v-model="subtaskSubject"
							@keydown.enter="createSubtask"
							@keydown.escape="showSubtaskAdd = false"
							type="text"
							placeholder="Subtask name..."
							class="flex-1 border border-gray-200 dark:border-gray-600 rounded px-2.5 py-1 text-xs bg-white dark:bg-gray-700 dark:text-gray-200 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
						/>
						<Button @click="createSubtask" :disabled="!subtaskSubject.trim()" size="sm" variant="solid" theme="blue" label="Add" />
					</div>
					<div v-if="childTasks.length" class="space-y-0.5">
						<div
							v-for="child in childTasks"
							:key="child.name"
							@click="taskStore.selectTask(child)"
							class="flex items-center gap-1.5 px-1.5 py-1 rounded hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer text-xs"
						>
							<div class="w-1.5 h-1.5 rounded-full flex-shrink-0" :class="childPriorityColor(child.priority)"></div>
							<FeatherIcon v-if="child.is_group" name="folder" class="w-3 h-3 text-blue-500 flex-shrink-0" />
							<span class="truncate" :class="child.status === 'Completed' ? 'text-gray-400 line-through' : 'text-gray-700 dark:text-gray-300'">{{ child.subject }}</span>
							<FeatherIcon v-if="child.status === 'Completed'" name="check" class="w-3 h-3 text-green-500 ml-auto flex-shrink-0" />
						</div>
					</div>
					<div v-else-if="!showSubtaskAdd" class="text-[11px] text-gray-400 dark:text-gray-500">No subtasks</div>
				</div>

				<!-- Comments -->
				<div>
					<h3 class="text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-1">Comments</h3>
					<div class="space-y-2">
						<div v-for="comment in comments" :key="comment.name" class="bg-gray-50 dark:bg-gray-700/50 rounded p-2">
							<div class="flex items-center gap-1.5 mb-0.5">
								<span class="text-[11px] font-medium text-gray-700 dark:text-gray-300">{{ comment.comment_by }}</span>
								<span class="text-[10px] text-gray-400">{{ formatTime(comment.creation) }}</span>
							</div>
							<div class="text-xs text-gray-600 dark:text-gray-300" v-html="comment.content"></div>
						</div>
					</div>
					<div class="mt-2 flex gap-1.5">
						<input v-model="newComment" @keydown.enter="addComment" type="text" placeholder="Add a comment..." class="flex-1 border border-gray-200 dark:border-gray-600 rounded px-2.5 py-1 text-xs bg-white dark:bg-gray-700 dark:text-gray-200 dark:placeholder-gray-400" />
						<Button @click="addComment" size="sm" variant="solid" theme="blue" label="Send" :disabled="!newComment.trim()" />
					</div>
				</div>
			</div>

			<div v-else class="flex-1 flex items-center justify-center">
				<LoadingIndicator class="w-6 h-6" />
			</div>
		</div>
	</transition>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import { getDoc, saveDoc, call } from '@/data/api'
import PrioritySlider from '@/components/common/PrioritySlider.vue'
import RecurrenceEditor from '@/components/common/RecurrenceEditor.vue'
import LinkField from '@/components/common/LinkField.vue'
import TaskAttachments from '@/components/task/TaskAttachments.vue'
import DatetimePicker from '@/components/common/DatetimePicker.vue'
import InstallationPanel from '@/components/task/InstallationPanel.vue'
import dayjs from 'dayjs'

const taskStore = useTaskStore()
const doc = ref<any>(null)
const saveError = ref('')
const comments = ref<any[]>([])
const newComment = ref('')
const assignees = ref<Array<{ email: string; full_name: string }>>([])
const userSearch = ref('')
const userResults = ref<Array<{ name: string; full_name: string }>>([])
const showUserDropdown = ref(false)
const childTasks = ref<any[]>([])
const showSubtaskAdd = ref(false)
const subtaskSubject = ref('')
const subtaskInput = ref<HTMLInputElement | null>(null)

const isCompleted = computed(() => doc.value && doc.value.status === 'Completed')
const isInstallation = computed(() => !!doc.value?.custom_installation_job)

async function onInstallationChanged() {
	if (!doc.value?.name) return
	try {
		const fresh = await getDoc('Task', doc.value.name)
		if (fresh) doc.value = fresh
	} catch { /* keep current state */ }
	taskStore.fetchTasks()
}

watch(() => taskStore.selectedTask, async (task) => {
	if (!task) { doc.value = null; return }
	try {
		doc.value = await getDoc('Task', task.name)
		await Promise.all([loadComments(), loadAssignees(), loadChildTasks()])
	} catch (e) {
		console.error('Failed to load task:', e)
	}
}, { immediate: true })

let saveTimeout: ReturnType<typeof setTimeout> | null = null

function debouncedSave() {
	if (saveTimeout) clearTimeout(saveTimeout)
	saveTimeout = setTimeout(save, 300)
}

async function save() {
	if (!doc.value) return
	saveError.value = ''
	try {
		const saved = await saveDoc(doc.value)
		if (saved && doc.value) {
			Object.assign(doc.value, {
				modified: saved.modified,
				docstatus: saved.docstatus,
				_assign: saved._assign,
			})
		}
		taskStore.fetchTasks()
	} catch (e: any) {
		const msg = e?.message || 'Failed to save'
		saveError.value = msg
		console.error('Failed to save:', msg)
		if (doc.value?.name) {
			try {
				const fresh = await getDoc('Task', doc.value.name)
				if (fresh) doc.value = fresh
			} catch { /* keep current state if reload also fails */ }
		}
	}
}

async function loadComments() {
	if (!doc.value) return
	try {
		comments.value = await call('taskist.api.get_task_comments', { task_name: doc.value.name }) || []
	} catch { comments.value = [] }
}

async function addComment() {
	if (!newComment.value.trim() || !doc.value) return
	try {
		await call('taskist.api.add_task_comment', { task_name: doc.value.name, content: newComment.value.trim() })
		newComment.value = ''
		await loadComments()
	} catch (e) {
		console.error('Failed to add comment:', e)
	}
}

async function loadAssignees() {
	if (!doc.value) return
	try {
		const assignStr = doc.value._assign
		if (!assignStr) { assignees.value = []; return }
		const emails = JSON.parse(assignStr)
		assignees.value = emails.map((email: string) => ({ email, full_name: email.split('@')[0] }))
		for (const a of assignees.value) {
			try {
				const user = await getDoc('User', a.email)
				if (user?.full_name) a.full_name = user.full_name
			} catch { /* keep email as fallback */ }
		}
	} catch { assignees.value = [] }
}

let searchTimeout: ReturnType<typeof setTimeout> | null = null

function searchUsers() {
	showUserDropdown.value = true
	if (searchTimeout) clearTimeout(searchTimeout)
	searchTimeout = setTimeout(async () => {
		if (!userSearch.value.trim()) { userResults.value = []; return }
		try {
			userResults.value = await call('taskist.api.search_users', { query: userSearch.value })
		} catch { userResults.value = [] }
	}, 200)
}

async function assignToMe() {
	if (!doc.value) return
	try {
		const user = await call('frappe.auth.get_logged_user')
		if (user && !assignees.value.some(a => a.email === user)) {
			await addAssignee(user)
		}
	} catch (e) {
		console.error('Failed to get current user:', e)
	}
}

async function addAssignee(email: string) {
	if (!doc.value) return
	showUserDropdown.value = false
	userSearch.value = ''
	userResults.value = []
	try {
		const result = await call('taskist.api.assign_task', { task_name: doc.value.name, user: email })
		assignees.value = result || []
		taskStore.fetchTasks()
	} catch (e) {
		console.error('Failed to assign:', e)
	}
}

async function removeAssignee(email: string) {
	if (!doc.value) return
	try {
		const result = await call('taskist.api.unassign_task', { task_name: doc.value.name, user: email })
		assignees.value = result || []
		taskStore.fetchTasks()
	} catch (e) {
		console.error('Failed to unassign:', e)
	}
}

async function markCompleted() {
	if (!doc.value) return
	doc.value.status = isCompleted.value ? 'Open' : 'Completed'
	await save()
}

async function loadChildTasks() {
	if (!doc.value) { childTasks.value = []; return }
	try {
		childTasks.value = await call('taskist.api.get_child_tasks', { parent_task: doc.value.name })
	} catch { childTasks.value = [] }
}

async function createSubtask() {
	if (!subtaskSubject.value.trim() || !doc.value) return
	try {
		await taskStore.quickCreate({
			subject: subtaskSubject.value.trim(),
			parent_task: doc.value.name,
			project: doc.value.project || undefined,
			priority: 'Medium',
		})
		subtaskSubject.value = ''
		showSubtaskAdd.value = false
		await loadChildTasks()
	} catch (e) {
		console.error('Failed to create subtask:', e)
	}
}

function childPriorityColor(priority: string) {
	const colors: Record<string, string> = { High: 'bg-orange-500', Medium: 'bg-yellow-500', Low: 'bg-green-500' }
	return colors[priority] || 'bg-gray-400'
}

function formatTime(dt: string) {
	return dayjs(dt).format('MMM D, h:mm A')
}
</script>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: transform 0.2s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); }
</style>
