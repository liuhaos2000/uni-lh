<template>
	<view class="etf-selector">
		<view class="etf-selector-row">
			<view class="etf-selector-input-wrap">
				<input
					class="etf-selector-input"
					:value="modelValue"
					:placeholder="placeholder"
					@input="onInput"
					@confirm="onAdd"
				/>
				<text v-if="candidates && candidates.length" class="etf-selector-arrow" @click="openPanel">
					▼
				</text>
			</view>
			<button class="etf-selector-btn" type="primary" size="mini" :loading="loading" @click="onAdd">
				添加
			</button>
		</view>

		<view v-if="open" class="etf-popup-mask" @click="closePanel">
			<view class="etf-popup-panel" :style="panelStyle" @click.stop>
				<view class="etf-popup-header">
					<input
						class="etf-popup-search"
						v-model="keyword"
						placeholder="搜索代码或名称"
						:adjust-position="false"
						confirm-type="search"
					/>
					<text class="etf-popup-cancel" @click="closePanel">取消</text>
				</view>
				<scroll-view scroll-y class="etf-popup-list">
					<view
						v-for="item in filtered"
						:key="item.code"
						class="etf-popup-item"
						@touchstart="onItemTouchStart"
						@touchmove="onItemTouchMove"
						@touchend="onItemTouchEnd($event, item)"
					>
						<text class="etf-popup-item-code">{{ item.code }}</text>
						<text class="etf-popup-item-name">{{ item.name || '' }}</text>
					</view>
					<view v-if="!filtered.length" class="etf-popup-empty">
						{{ candidates && candidates.length ? '无匹配项' : '关注列表为空，可直接输入代码' }}
					</view>
				</scroll-view>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'

const props = defineProps({
	modelValue: { type: String, default: '' },
	candidates: { type: Array, default: () => [] },
	loading: { type: Boolean, default: false },
	placeholder: { type: String, default: '输入ETF代码或从关注列表选择' },
})

const emit = defineEmits(['update:modelValue', 'add'])

const open = ref(false)
const keyword = ref('')
const kbHeight = ref(0)
const touchStartPos = { x: 0, y: 0, moved: false }
const TAP_SLOP = 10

const filtered = computed(() => {
	const kw = keyword.value.trim().toLowerCase()
	const list = props.candidates || []
	if (!kw) return list
	return list.filter(it => {
		const code = String(it.code || '').toLowerCase()
		const name = String(it.name || '').toLowerCase()
		return code.indexOf(kw) >= 0 || name.indexOf(kw) >= 0
	})
})

const panelStyle = computed(() => ({
	marginBottom: `${kbHeight.value}px`,
}))

function onKbChange(res) {
	kbHeight.value = (res && res.height) || 0
}

function openPanel() {
	keyword.value = ''
	open.value = true
	if (typeof uni !== 'undefined' && uni.onKeyboardHeightChange) {
		uni.onKeyboardHeightChange(onKbChange)
	}
}

function closePanel() {
	open.value = false
	kbHeight.value = 0
	if (typeof uni !== 'undefined' && uni.offKeyboardHeightChange) {
		uni.offKeyboardHeightChange(onKbChange)
	}
}

function onInput(e) {
	const val = e && e.detail ? e.detail.value : ''
	emit('update:modelValue', val)
}

function pick(item) {
	emit('update:modelValue', item.code)
	closePanel()
}

function onItemTouchStart(e) {
	const t = (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0])
	touchStartPos.x = t ? t.pageX : 0
	touchStartPos.y = t ? t.pageY : 0
	touchStartPos.moved = false
}

function onItemTouchMove(e) {
	const t = (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0])
	if (!t) return
	if (Math.abs(t.pageX - touchStartPos.x) > TAP_SLOP || Math.abs(t.pageY - touchStartPos.y) > TAP_SLOP) {
		touchStartPos.moved = true
	}
}

function onItemTouchEnd(e, item) {
	if (touchStartPos.moved) return
	pick(item)
}

function onAdd() {
	closePanel()
	emit('add')
}

onBeforeUnmount(() => {
	if (typeof uni !== 'undefined' && uni.offKeyboardHeightChange) {
		uni.offKeyboardHeightChange(onKbChange)
	}
})
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

.etf-popup-mask {
	position: fixed;
	left: 0;
	right: 0;
	top: 0;
	bottom: 0;
	background: rgba(0, 0, 0, 0.45);
	z-index: 9999;
	display: flex;
	align-items: flex-end;
	justify-content: center;
}

.etf-popup-panel {
	width: 100%;
	max-width: 640px;
	background: #fff;
	border-top-left-radius: 12px;
	border-top-right-radius: 12px;
	max-height: 70vh;
	display: flex;
	flex-direction: column;
	box-sizing: border-box;
	transition: margin-bottom 0.2s ease;
}

.etf-popup-header {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 10px 12px;
	border-bottom: 1px solid #eee;
	flex-shrink: 0;
}

.etf-popup-search {
	flex: 1;
	font-size: 14px;
	padding: 8px 10px;
	border: 1px solid #ddd;
	border-radius: 4px;
	background: #fafafa;
}

.etf-popup-cancel {
	font-size: 14px;
	color: #5470c6;
	padding: 4px 6px;
}

.etf-popup-list {
	flex: 1;
	min-height: 0;
	max-height: 60vh;
}

.etf-popup-item {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 12px 14px;
	border-bottom: 1px solid #f3f3f3;
}

.etf-popup-item:last-child {
	border-bottom: none;
}

.etf-popup-item-code {
	font-size: 14px;
	font-weight: 600;
	color: #5470c6;
	min-width: 60px;
}

.etf-popup-item-name {
	font-size: 14px;
	color: #333;
	flex: 1;
}

.etf-popup-empty {
	padding: 24px;
	text-align: center;
	font-size: 13px;
	color: #999;
}
</style>
