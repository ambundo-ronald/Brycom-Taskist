<template>
	<div class="border border-blue-200 dark:border-blue-800 rounded-lg overflow-hidden">
		<div class="flex items-center justify-between px-3 py-2 bg-blue-50 dark:bg-blue-900/30">
			<div class="flex items-center gap-1.5 min-w-0">
				<FeatherIcon name="truck" class="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0" />
				<span class="text-xs font-semibold text-blue-800 dark:text-blue-200 truncate">Installation {{ job?.name || '' }}</span>
			</div>
			<Badge v-if="job" :label="job.state" size="sm" :theme="stateTheme" />
		</div>

		<div v-if="loading && !job" class="p-4 flex justify-center"><LoadingIndicator class="w-5 h-5" /></div>

		<div v-else-if="job" class="p-3 space-y-3">
			<div v-if="error" class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded px-3 py-2 text-xs text-red-700 dark:text-red-300 whitespace-pre-line">{{ error }}</div>

			<!-- Job details -->
			<div class="grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs">
				<div>
					<div class="text-[11px] text-gray-400 dark:text-gray-500">Customer</div>
					<div class="font-medium text-gray-800 dark:text-gray-200">{{ job.customer }}</div>
				</div>
				<div>
					<div class="text-[11px] text-gray-400 dark:text-gray-500">Phone</div>
					<a v-if="job.contact_phone" :href="`tel:${job.contact_phone}`" class="font-medium text-blue-600 dark:text-blue-400">{{ job.contact_phone }}</a>
					<span v-else class="text-gray-400">-</span>
				</div>
				<div>
					<div class="text-[11px] text-gray-400 dark:text-gray-500">Location</div>
					<div class="font-medium text-gray-800 dark:text-gray-200">{{ job.location || '-' }}</div>
				</div>
				<div>
					<div class="text-[11px] text-gray-400 dark:text-gray-500">Date</div>
					<div class="font-medium text-gray-800 dark:text-gray-200">{{ job.installation_date ? formatDate(job.installation_date) : '-' }}</div>
				</div>
				<div class="col-span-2">
					<div class="text-[11px] text-gray-400 dark:text-gray-500">Collect from</div>
					<div class="font-medium text-gray-800 dark:text-gray-200">{{ job.source_warehouse }}</div>
				</div>
			</div>

			<!-- Step 1: accept receipt -->
			<div v-if="job.state === 'Assigned'" class="space-y-2">
				<div class="text-[11px] font-medium text-gray-500 dark:text-gray-400">Devices to collect ({{ job.devices.length }})</div>
				<div v-for="d in job.devices" :key="d.name" class="flex items-center justify-between text-xs bg-gray-50 dark:bg-gray-700/50 rounded px-2 py-1.5">
					<div>
						<div class="font-medium text-gray-800 dark:text-gray-200">{{ d.item_code }}</div>
						<div class="font-mono text-[11px] text-gray-500 dark:text-gray-400">{{ d.serial_no }}</div>
					</div>
					<Badge :label="supplyLabel(d.supply_type)" size="sm" :theme="d.supply_type === 'Sold' ? 'green' : 'blue'" />
				</div>
				<template v-if="job.is_my_job">
					<label class="flex items-start gap-2 text-xs text-gray-700 dark:text-gray-300 pt-1">
						<input v-model="confirmReceipt" type="checkbox" class="mt-0.5" />
						<span>I have physically received all {{ job.devices.length }} device(s) listed above and checked the IMEI numbers.</span>
					</label>
					<Button
						class="w-full"
						variant="solid"
						theme="blue"
						:loading="busy"
						:disabled="!confirmReceipt"
						label="Accept Receipt"
						@click="accept"
					/>
				</template>
				<div v-else class="text-[11px] text-gray-400">Waiting for {{ job.technician_name || job.technician }} to accept the devices.</div>
			</div>

			<!-- Step 2: install, enter vehicle details -->
			<div v-else-if="job.state === 'Accepted'" class="space-y-2">
				<div class="text-[11px] text-gray-400">Received {{ job.accepted_on ? formatDateTime(job.accepted_on) : '' }}. Enter each vehicle's details, then mark the job installed.</div>
				<div v-for="d in form" :key="d.name" class="border border-gray-200 dark:border-gray-600 rounded-lg p-2 space-y-1.5">
					<div class="flex items-center justify-between">
						<div class="text-xs">
							<span class="font-medium text-gray-800 dark:text-gray-200">{{ d.item_code }}</span>
							<span class="font-mono text-[11px] text-gray-500 dark:text-gray-400 ml-1">{{ d.serial_no }}</span>
						</div>
						<Badge :label="supplyLabel(d.supply_type)" size="sm" :theme="d.supply_type === 'Sold' ? 'green' : 'blue'" />
					</div>
					<div class="grid grid-cols-2 gap-1.5">
						<div class="col-span-2">
							<label class="field-label">Vehicle Reg No *</label>
							<input v-model="d.vehicle_reg" :disabled="!job.is_my_job" class="field-input uppercase" placeholder="KDA 123X" />
						</div>
						<div>
							<label class="field-label">Make / Model</label>
							<input v-model="d.vehicle_make_model" :disabled="!job.is_my_job" class="field-input" placeholder="Toyota Premio" />
						</div>
						<div>
							<label class="field-label">Colour</label>
							<input v-model="d.colour" :disabled="!job.is_my_job" class="field-input" />
						</div>
						<div class="col-span-2">
							<label class="field-label">Registered Owner</label>
							<input v-model="d.registered_owner" :disabled="!job.is_my_job" class="field-input" placeholder="As on the logbook" />
						</div>
						<div class="col-span-2">
							<label class="field-label">Financier (joint owner)</label>
							<LinkField
								:model-value="d.financier || ''"
								@update:model-value="(v: string) => { d.financier = v }"
								placeholder="Bank / Sacco, if any"
								search-method="taskist.brycom.search_financiers"
							/>
						</div>
						<div>
							<label class="field-label">Chassis No</label>
							<input v-model="d.chassis_no" :disabled="!job.is_my_job" class="field-input uppercase" />
						</div>
						<div>
							<label class="field-label">Engine No</label>
							<input v-model="d.engine_no" :disabled="!job.is_my_job" class="field-input uppercase" />
						</div>
						<div class="col-span-2">
							<label class="field-label">SIM Number</label>
							<input v-model="d.sim_number" :disabled="!job.is_my_job" class="field-input" />
						</div>
					</div>
				</div>
				<div>
					<label class="field-label">Notes for the office</label>
					<FrappeTextarea v-model="notes" :rows="2" :disabled="!job.is_my_job" placeholder="Anything the salesperson should know..." />
				</div>
				<div class="text-[11px] text-gray-400">Add installation photos under Attachments below.</div>
				<div v-if="job.is_my_job" class="grid grid-cols-2 gap-2">
					<Button variant="subtle" :loading="busy" label="Save" @click="saveDetails" />
					<Button variant="solid" theme="green" :loading="busy" :disabled="!allRegsEntered" label="Mark Installed" @click="markInstalled" />
				</div>
			</div>

			<!-- Done / other states -->
			<div v-else class="space-y-1.5">
				<div v-for="d in job.devices" :key="d.name" class="flex items-center justify-between text-xs bg-gray-50 dark:bg-gray-700/50 rounded px-2 py-1.5">
					<div>
						<div class="font-medium text-gray-800 dark:text-gray-200">{{ d.vehicle_reg || d.item_code }}</div>
						<div class="font-mono text-[11px] text-gray-500 dark:text-gray-400">{{ d.item_code }} · {{ d.serial_no }}</div>
					</div>
					<Badge :label="d.device_status" size="sm" theme="gray" />
				</div>
				<div v-if="job.state === 'Installed'" class="text-[11px] text-green-600 dark:text-green-400">Installed {{ job.installed_on ? formatDateTime(job.installed_on) : '' }}. The salesperson has been notified to invoice.</div>
				<div v-else-if="job.state === 'Completed'" class="text-[11px] text-green-600 dark:text-green-400">Invoiced and completed.</div>
				<div v-else-if="job.state === 'Returned'" class="text-[11px] text-gray-500">Devices were returned unused.</div>
				<div v-else-if="job.state === 'Draft'" class="text-[11px] text-gray-500">This job was recalled by the salesperson.</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { call } from '@/data/api'
import LinkField from '@/components/common/LinkField.vue'
import dayjs from 'dayjs'

const props = defineProps<{ taskName: string }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const EDITABLE = ['vehicle_reg', 'vehicle_make_model', 'sim_number', 'registered_owner', 'financier', 'chassis_no', 'engine_no', 'colour'] as const

const job = ref<any>(null)
const form = ref<any[]>([])
const notes = ref('')
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const confirmReceipt = ref(false)

const stateTheme = computed(() => {
	const map: Record<string, string> = { Assigned: 'orange', Accepted: 'blue', Installed: 'green', Completed: 'green', Returned: 'gray', Draft: 'gray', Cancelled: 'red' }
	return map[job.value?.state] || 'gray'
})

const allRegsEntered = computed(() => form.value.length > 0 && form.value.every(d => (d.vehicle_reg || '').trim()))

function setJob(data: any) {
	job.value = data
	form.value = (data?.devices || []).map((d: any) => ({ ...d }))
	notes.value = data?.technician_notes || ''
	confirmReceipt.value = false
}

async function load() {
	if (!props.taskName) return
	loading.value = true
	error.value = ''
	try {
		setJob(await call('taskist.brycom.get_installation', { task_name: props.taskName }))
	} catch (e: any) {
		error.value = e?.message || 'Could not load the installation job'
	} finally {
		loading.value = false
	}
}

function payload() {
	return form.value.map(d => {
		const row: Record<string, any> = { name: d.name }
		for (const f of EDITABLE) row[f] = f === 'vehicle_reg' || f === 'chassis_no' || f === 'engine_no' ? (d[f] || '').toUpperCase() : d[f]
		return row
	})
}

async function run(method: string, args: Record<string, any>) {
	busy.value = true
	error.value = ''
	try {
		setJob(await call(method, { task_name: props.taskName, ...args }))
		emit('changed')
	} catch (e: any) {
		error.value = e?.message || 'Something went wrong'
	} finally {
		busy.value = false
	}
}

function accept() {
	return run('taskist.brycom.accept_installation_receipt', {})
}

function saveDetails() {
	return run('taskist.brycom.save_installation_details', { devices: payload(), notes: notes.value })
}

function markInstalled() {
	if (!allRegsEntered.value) return
	return run('taskist.brycom.complete_installation', { devices: payload(), notes: notes.value })
}

function supplyLabel(t: string) {
	return t === 'Sold' ? 'Sold' : 'Brycomm-owned'
}

function formatDate(d: string) {
	return dayjs(d).format('ddd, MMM D')
}

function formatDateTime(d: string) {
	return dayjs(d).format('MMM D, h:mm A')
}

watch(() => props.taskName, load, { immediate: true })

defineExpose({ reload: load })
</script>

<style scoped>
.field-label {
	@apply block text-[11px] font-medium text-gray-400 dark:text-gray-500 mb-0.5;
}
.field-input {
	@apply w-full border border-gray-200 dark:border-gray-600 rounded px-2 py-1 text-xs bg-white dark:bg-gray-700 dark:text-gray-200 disabled:opacity-60;
}
</style>
