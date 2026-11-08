<template>
	<div>
		<div class="flex items-center justify-between mb-2">
			<h3 class="text-xs font-medium text-gray-500 dark:text-gray-400">{{ title || 'Attachments' }}</h3>
			<label class="cursor-pointer p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400">
				<FeatherIcon name="plus" class="w-4 h-4" />
				<input type="file" class="hidden" @change="uploadFile" multiple :disabled="uploading" :accept="title === 'Installation photos' ? 'image/*' : undefined" />
			</label>
		</div>

		<div v-if="uploading" class="text-xs text-gray-400 dark:text-gray-500 mb-2">Uploading...</div>

		<div v-if="attachments.length" class="grid grid-cols-2 sm:grid-cols-3 gap-2">
			<div
				v-for="file in attachments"
				:key="file.name"
				class="group relative border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden bg-gray-50 dark:bg-gray-700/50"
			>
				<!-- Image thumbnail -->
				<a v-if="file.is_image" :href="file.file_url" target="_blank" class="block aspect-square">
					<img :src="file.thumbnail_url || file.file_url" :alt="file.file_name" class="w-full h-full object-cover" />
				</a>
				<!-- Document icon -->
				<a v-else :href="file.file_url" target="_blank" class="flex flex-col items-center justify-center aspect-square p-2 hover:bg-gray-100 dark:hover:bg-gray-600">
					<FeatherIcon name="file" class="w-8 h-8 text-gray-400 dark:text-gray-500 mb-1" />
					<span class="text-[10px] text-gray-500 dark:text-gray-400 uppercase font-medium">{{ file.file_ext }}</span>
				</a>
				<!-- File name overlay -->
				<div class="absolute bottom-0 left-0 right-0 bg-black/50 px-1.5 py-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
					<span class="text-[10px] text-white truncate block">{{ file.file_name }}</span>
				</div>
				<!-- Remove button -->
				<button
					@click.stop="removeFile(file.name)"
					class="absolute top-1 right-1 w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
					title="Remove attachment"
				>
					<FeatherIcon name="x" class="w-3 h-3" />
				</button>
			</div>
		</div>
		<div v-else class="text-xs text-gray-400 dark:text-gray-500">No attachments</div>
	</div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { call, getCSRFToken } from '@/data/api'

const props = defineProps<{ taskName: string; title?: string }>()

interface Attachment {
	name: string
	file_name: string
	file_url: string
	thumbnail_url: string | null
	file_size: number
	is_private: boolean
	file_ext: string
	is_image: boolean
}

const attachments = ref<Attachment[]>([])
const uploading = ref(false)

async function loadAttachments() {
	if (!props.taskName) return
	try {
		attachments.value = await call('taskist.api.get_attachments', { task_name: props.taskName })
	} catch {
		attachments.value = []
	}
}

async function uploadFile(event: Event) {
	const input = event.target as HTMLInputElement
	const files = input.files
	if (!files || !files.length) return

	uploading.value = true
	try {
		for (const file of Array.from(files)) {
			const formData = new FormData()
			formData.append('file', file)
			formData.append('doctype', 'Task')
			formData.append('docname', props.taskName)
			formData.append('is_private', '0')

			await fetch('/api/method/upload_file', {
				method: 'POST',
				body: formData,
				headers: {
					'X-Frappe-CSRF-Token': getCSRFToken(),
				},
			})
		}
		await loadAttachments()
	} catch (e) {
		console.error('Failed to upload:', e)
	} finally {
		uploading.value = false
		input.value = ''
	}
}

async function removeFile(fileName: string) {
	try {
		await call('taskist.api.remove_attachment', { file_name: fileName })
		attachments.value = attachments.value.filter(f => f.name !== fileName)
	} catch (e) {
		console.error('Failed to remove attachment:', e)
	}
}

watch(() => props.taskName, loadAttachments, { immediate: true })
</script>
