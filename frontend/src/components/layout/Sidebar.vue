<template>
	<aside
		class="h-full bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col transition-all duration-200"
		:class="collapsed ? 'w-16' : 'w-64'"
	>
		<div class="h-14 flex items-center px-4 border-b border-gray-200 dark:border-gray-700">
			<button @click="$emit('toggle')" class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
				<FeatherIcon name="menu" class="w-6 h-6 text-gray-600 dark:text-gray-400" />
			</button>
			<span v-if="!collapsed" class="ml-3 font-bold text-lg text-blue-600">Taskist</span>
		</div>

		<div v-if="!collapsed" class="p-4 flex-1 overflow-auto">
			<div v-if="taskStore.isTechnician" class="text-sm text-gray-600 dark:text-gray-300">
				<h3 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">My Jobs</h3>
				<button class="w-full text-left px-3 py-2 rounded-lg text-sm mb-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium">
					All my installation tasks
				</button>
			</div>
			<template v-else>
			<div class="flex items-center justify-between mb-3">
				<h3 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Projects</h3>
				<button
					@click="showProjectDialog = true"
					class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
					title="New Project"
				>
					<FeatherIcon name="plus" class="w-4 h-4" />
				</button>
			</div>

			<button
				class="w-full text-left px-3 py-2 rounded-lg text-sm mb-1 transition-colors"
				:class="selectedProject === '' ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
				@click="selectProject('')"
			>
				All Tasks
			</button>
			<button
				class="w-full text-left px-3 py-2 rounded-lg text-sm mb-1 transition-colors"
				:class="selectedProject === '__no_project__' ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
				@click="selectProject('__no_project__')"
			>
				Non-Project Tasks
			</button>
			<button
				v-for="project in projects"
				:key="project"
				class="w-full text-left px-3 py-2 rounded-lg text-sm mb-1 transition-colors"
				:class="selectedProject === project ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
				@click="selectProject(project)"
			>
				{{ project }}
			</button>
			</template>
		</div>

	</aside>
	<Teleport to="body">
		<ProjectDialog v-if="showProjectDialog" @close="showProjectDialog = false" @created="loadProjects" />
	</Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getList } from '@/data/api'
import { useTaskStore } from '@/stores/taskStore'
import ProjectDialog from '@/components/common/ProjectDialog.vue'

defineProps<{ collapsed: boolean }>()
defineEmits(['toggle'])

const taskStore = useTaskStore()
const projects = ref<string[]>([])
const selectedProject = ref('')
const showProjectDialog = ref(false)

async function loadProjects() {
	try {
		const result = await getList('Project', {
			fields: ['name'],
			filters: { status: 'Open' },
			order_by: 'name asc',
			limit_page_length: 50,
		})
		projects.value = result.map((p: any) => p.name)
	} catch {
		// Projects module might not be available
	}
}

function selectProject(project: string) {
	selectedProject.value = project
	if (!project) {
		taskStore.filters = {}
	} else if (project === '__no_project__') {
		taskStore.filters = { project: ['is', 'not set'] }
	} else {
		taskStore.filters = { project }
	}
	taskStore.fetchTasks()
}

onMounted(async () => {
	await taskStore.loadUserContext()
	if (!taskStore.isTechnician) loadProjects()
})
</script>
