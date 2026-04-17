<template>
	<view v-if="modelValue" class="sub-dialog-mask" @click="onCancel">
		<view class="sub-dialog-card" @click.stop>
			<text class="sub-dialog-title">{{ title }}</text>
			<text v-if="hint" class="sub-dialog-hint">{{ hint }}</text>
			<input
				class="sub-dialog-input"
				v-model="inner"
				:placeholder="placeholder"
				:focus="modelValue"
				maxlength="30"
				confirm-type="done"
				@confirm="onConfirm"
			/>
			<view class="sub-dialog-actions">
				<button
					class="sub-dialog-btn sub-dialog-btn-cancel"
					size="mini"
					:disabled="loading"
					@click="onCancel"
				>取消</button>
				<button
					class="sub-dialog-btn sub-dialog-btn-ok"
					size="mini"
					:loading="loading"
					@click="onConfirm"
				>保存</button>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
	modelValue: { type: Boolean, default: false },
	title: { type: String, default: '订阅命名' },
	hint: { type: String, default: '给这个订阅起个名字，方便以后查找。' },
	placeholder: { type: String, default: '例如：科创50 每日动量' },
	defaultName: { type: String, default: '' },
	loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const inner = ref('')

watch(
	() => props.modelValue,
	(v) => {
		if (v) inner.value = props.defaultName || ''
	},
	{ immediate: true },
)

function onCancel() {
	if (props.loading) return
	emit('update:modelValue', false)
}

function onConfirm() {
	const name = (inner.value || '').trim()
	emit('confirm', name)
}
</script>

<style scoped>
.sub-dialog-mask {
	position: fixed;
	left: 0;
	right: 0;
	top: 0;
	bottom: 0;
	background: rgba(0, 0, 0, 0.45);
	z-index: 9999;
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 24px;
	box-sizing: border-box;
}

.sub-dialog-card {
	width: 100%;
	max-width: 320px;
	background: #fff;
	border-radius: 8px;
	padding: 18px 16px 14px;
	box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
	display: flex;
	flex-direction: column;
	gap: 8px;
	box-sizing: border-box;
}

.sub-dialog-title {
	font-size: 16px;
	font-weight: 600;
	color: #333;
}

.sub-dialog-hint {
	font-size: 12px;
	color: #999;
	line-height: 1.5;
}

.sub-dialog-input {
	border: 1px solid #ddd;
	border-radius: 4px;
	padding: 8px 10px;
	font-size: 14px;
	background: #fafafa;
	margin-top: 4px;
}

.sub-dialog-actions {
	display: flex;
	gap: 8px;
	margin-top: 10px;
	justify-content: flex-end;
}

.sub-dialog-btn {
	min-width: 72px;
	font-size: 13px !important;
	margin: 0 !important;
}

.sub-dialog-btn-cancel {
	background: #f3f4f6 !important;
	color: #666 !important;
	border: 1px solid #e5e7eb !important;
}

.sub-dialog-btn-ok {
	background: #ffa200 !important;
	color: #fff !important;
	border: none !important;
}

.sub-dialog-btn-ok[disabled] {
	opacity: 0.7;
}
</style>
