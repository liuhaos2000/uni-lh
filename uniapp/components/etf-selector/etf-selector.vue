<template>
	<view class="etf-selector">
		<view class="etf-selector-row">
			<view class="etf-selector-input-wrap">
				<input
					class="etf-selector-input"
					:value="modelValue"
					:placeholder="placeholder"
					@input="onInput"
					@focus="onFocus"
					@blur="onBlur"
					@confirm="onAdd"
				/>
				<text v-if="candidates && candidates.length" class="etf-selector-arrow" @click="toggle">
					{{ open ? '▲' : '▼' }}
				</text>
			</view>
			<button class="etf-selector-btn" type="primary" size="mini" :loading="loading" @click="onAdd">
				添加
			</button>
		</view>
		<view v-if="open && filtered.length" class="etf-selector-dropdown">
			<scroll-view scroll-y class="etf-selector-scroll">
				<view
					v-for="item in filtered"
					:key="item.code"
					class="etf-selector-item"
					@mousedown.prevent="pick(item)"
					@touchend.stop.prevent="pick(item)"
				>
					<text class="etf-selector-item-code">{{ item.code }}</text>
					<text class="etf-selector-item-name">{{ item.name || '' }}</text>
				</view>
			</scroll-view>
		</view>
		<view v-else-if="open && (!candidates || !candidates.length)" class="etf-selector-dropdown">
			<view class="etf-selector-empty">关注列表为空，可直接输入代码</view>
		</view>
	</view>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
	modelValue: { type: String, default: '' },
	candidates: { type: Array, default: () => [] },
	loading: { type: Boolean, default: false },
	placeholder: { type: String, default: '输入ETF代码或从关注列表选择' },
})

const emit = defineEmits(['update:modelValue', 'add'])

const open = ref(false)
let blurTimer = null

const filtered = computed(() => {
	const kw = (props.modelValue || '').trim().toLowerCase()
	const list = props.candidates || []
	if (!kw) return list
	return list.filter(it => {
		const code = String(it.code || '').toLowerCase()
		const name = String(it.name || '').toLowerCase()
		return code.indexOf(kw) >= 0 || name.indexOf(kw) >= 0
	})
})

function onInput(e) {
	const val = e && e.detail ? e.detail.value : ''
	emit('update:modelValue', val)
	open.value = true
}

function onFocus() {
	if (blurTimer) { clearTimeout(blurTimer); blurTimer = null }
	open.value = true
}

function onBlur() {
	blurTimer = setTimeout(() => { open.value = false }, 200)
}

function toggle() {
	open.value = !open.value
}

function pick(item) {
	emit('update:modelValue', item.code)
	open.value = false
}

function onAdd() {
	open.value = false
	emit('add')
}
</script>

<style scoped>
.etf-selector {
	position: relative;
	width: 100%;
}

.etf-selector-row {
	display: flex;
	align-items: center;
	gap: 8px;
}

.etf-selector-input-wrap {
	flex: 1;
	max-width: 220px;
	position: relative;
	display: flex;
	align-items: center;
	border: 1px solid #ddd;
	border-radius: 4px;
	padding: 0 28px 0 10px;
	background: #fff;
}

.etf-selector-input {
	flex: 1;
	font-size: 14px;
	padding: 6px 0;
	border: none;
	background: transparent;
	outline: none;
}

.etf-selector-arrow {
	position: absolute;
	right: 8px;
	font-size: 10px;
	color: #999;
	padding: 4px;
	cursor: pointer;
}

.etf-selector-btn {
	flex-shrink: 0;
}

.etf-selector-dropdown {
	position: absolute;
	left: 0;
	top: 100%;
	width: 220px;
	max-width: 100%;
	margin-top: 4px;
	background: #fff;
	border: 1px solid #ddd;
	border-radius: 4px;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
	z-index: 50;
	max-height: 220px;
	overflow: hidden;
}

.etf-selector-scroll {
	max-height: 220px;
}

.etf-selector-item {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 8px 12px;
	cursor: pointer;
	border-bottom: 1px solid #f3f3f3;
}

.etf-selector-item:last-child {
	border-bottom: none;
}

.etf-selector-item:hover {
	background: #f5f8ff;
}

.etf-selector-item-code {
	font-size: 13px;
	font-weight: 600;
	color: #5470c6;
	min-width: 60px;
}

.etf-selector-item-name {
	font-size: 13px;
	color: #333;
	flex: 1;
}

.etf-selector-empty {
	padding: 12px;
	text-align: center;
	font-size: 12px;
	color: #999;
}
</style>
