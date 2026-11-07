<template>
	<div
		class="bg-white dark:bg-gray-800 rounded-lg border p-3 cursor-pointer hover:shadow-md transition-shadow"
		:class="cardBorderClass"
		@click="taskStore.selectTask(task)"
	>
		<div class="flex items-start gap-2">
			<div class="w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0" :style="dotStyle" :class="!task.color ? priorityColor : ''"></div>
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-1">
					<button
						v-if="childCount > 0"
						@click.stop="taskStore.toggleCollapse(task.name)"
						class="w-3.5 h-3.5 flex items-center justify-center flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-transform"
						:class="taskStore.isCollapsed(task.name) ? '' : 'rotate-90'"
						:title="taskStore.isCollapsed(task.name) ? 'Expand' : 'Collapse'"
					>
						<FeatherIcon name="chevron-right" class="w-3 h-3" />
					</button>
					<FeatherIcon v-if="task.is_group" name="folder" class="w-3.5 h-3.5 text-blue-500 flex-shrink-0" title="Group task" />
					<FeatherIcon v-if="task.is_milestone" name="star" class="w-3.5 h-3.5 text-amber-500 flex-shrink-0" title="Milestone" />
					<FeatherIcon v-if="task.custom_installation_job" name="truck" class="w-3.5 h-3.5 text-blue-600 flex-shrink-0" title="Installation job" />
					<p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{{ task.subject }}</p>
					<FeatherIcon v-if="task.taskist_is_recurring" name="refresh-cw" class="w-3.5 h-3.5 text-blue-500 flex-shrink-0" title="Recurring task" />
				</div>
				<!-- Progress bar if progress > 0 -->
				<div v-if="task.progress > 0" class="mt-1.5">
					<FrappeProgress :value="task.progress" size="sm" />
				</div>
				<div v-if="tags.length" class="flex flex-wrap gap-1 mt-1.5">
					<Badge v-for="tag in tags" :key="tag" :label="tag" size="sm" theme="gray" />
				</div>
				<div class="flex items-center gap-3 mt-2 text-xs text-gray-500 dark:text-gray-400">
					<span
						v-if="task.parent_task"
						@click.stop="taskStore.selectTask({ name: task.parent_task } as any)"
						class="flex items-center gap-0.5 text-purple-500 hover:text-purple-700 dark:hover:text-purple-300 cursor-pointer"
						:title="'Parent: ' + task.parent_task"
					>
						<FeatherIcon name="corner-up-left" class="w-3 h-3" />
					</span>
					<span v-if="childCount > 0" class="flex items-center gap-0.5 text-blue-500">
						<FeatherIcon name="folder" class="w-3 h-3" />
						{{ childCount }}
						<button
							@click.stop="taskStore.toggleGroupFilter(task.name)"
							class="ml-0.5 p-0.5 rounded hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
							:class="taskStore.groupFilter === task.name ? 'text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/40' : 'text-blue-400 hover:text-blue-600'"
							:title="taskStore.groupFilter === task.name ? 'Clear filter' : 'Show only children'"
						>
							<FeatherIcon name="filter" class="w-3 h-3" />
						</button>
					</span>
					<span v-if="task.exp_end_date" class="flex items-center gap-1" :class="isOverdue ? 'text-red-500' : ''">
						{{ formatDate(task.exp_end_date) }}
					</span>
					<span v-if="task.type">
						<Badge :label="task.type" size="sm" theme="gray" />
					</span>
					<span v-if="task.project" class="truncate max-w-[100px]">{{ task.project }}</span>
					<div v-if="assignees.length" class="flex -space-x-1 ml-auto">
						<Avatar
							v-for="(user, i) in assignees.slice(0, 3)"
							:key="i"
							:label="user"
							size="xs"
							class="ring-2 ring-white dark:ring-gray-800"
							:title="user"
						/>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTaskStore, type Task } from '@/stores/taskStore'
import dayjs from 'dayjs'

const props = defineProps<{ task: Task & { _childCount?: number } }>()
const taskStore = useTaskStore()

const childCount = computed(() => {
	if (typeof props.task._childCount === 'number') return props.task._childCount
	return (taskStore.childrenMap[props.task.name] || []).length
})

const cardBorderClass = computed(() => {
	if (props.task.color) return 'border-l-4'
	return 'border-gray-200 dark:border-gray-700'
})

const dotStyle = computed(() => {
	if (props.task.color) return { backgroundColor: props.task.color }
	return {}
})

const priorityColor = computed(() => {
	const colors: Record<string, string> = { High: 'bg-orange-500', Medium: 'bg-yellow-500', Low: 'bg-green-500' }
	return colors[props.task.priority] || 'bg-gray-400'
})

const assignees = computed(() => {
	if (!props.task._assign) return []
	try { return JSON.parse(props.task._assign) } catch { return [] }
})

const tags = computed(() => {
	if (!props.task._user_tags) return []
	return props.task._user_tags.split(',').filter(Boolean)
})

const isOverdue = computed(() => {
	if (!props.task.exp_end_date) return false
	return dayjs(props.task.exp_end_date).isBefore(dayjs(), 'day')
})

function formatDate(date: string) {
	const d = dayjs(date)
	if (d.isSame(dayjs(), 'day')) return 'Today'
	if (d.isSame(dayjs().add(1, 'day'), 'day')) return 'Tomorrow'
	return d.format('MMM D')
}
</script>

<style scoped>
.border-l-4 {
	border-left-width: 4px;
	border-left-color: v-bind('task.color || "transparent"');
	border-top-color: rgb(229 231 235);
	border-right-color: rgb(229 231 235);
	border-bottom-color: rgb(229 231 235);
}
:is(.dark) .border-l-4 {
	border-top-color: rgb(55 65 81);
	border-right-color: rgb(55 65 81);
	border-bottom-color: rgb(55 65 81);
}
</style>
