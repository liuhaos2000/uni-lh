<!-- 本示例未包含完整css，获取外链css请参考上文，在hello uni-app项目中查看 -->
<template>
    <view>
        <view>
            <form @submit="formSubmit" @reset="formReset">
                <view class="uni-form-item uni-column">
                    <view class="title">switch</view>
                    <view>
                        <switch name="switch" :checked="formData.switch" @change="onSwitchChange" />
                    </view>
                </view>
                <view class="uni-form-item uni-column">
                    <view class="title">radio</view>
                    <radio-group name="radio" @change="onRadioChange">
                        <label v-for="option in FORM_DEFAULTS.RADIO_OPTIONS" :key="option.value">
                            <radio :value="option.value" :checked="formData.radio === option.value" />
                            <text>{{ option.label }}</text>
                        </label>
                    </radio-group>
                </view>
                <view class="uni-form-item uni-column">
                    <view class="title">checkbox</view>
                    <checkbox-group name="checkbox" @change="onCheckboxChange">
                        <label v-for="option in FORM_DEFAULTS.CHECKBOX_OPTIONS" :key="option.value">
                            <checkbox :value="option.value" :checked="formData.checkbox.includes(option.value)" />
                            <text>{{ option.label }}</text>
                        </label>
                    </checkbox-group>
                </view>
                <view class="uni-form-item uni-column">
                    <view class="title">slider</view>
                    <slider :value="formData.slider" name="slider" show-value @change="onSliderChange"></slider>
                </view>
                <view class="uni-form-item uni-column">
                    <view class="title">input</view>
                    <input class="uni-input" name="input" :value="formData.input" @input="onInputChange"
                        placeholder="这是一个输入框" />
                </view>
                <view class="uni-btn-v">
                    <button form-type="submit">Submit</button>
                    <button type="default" form-type="reset">Reset</button>
                </view>
            </form>
        </view>
    </view>
</template>
<script>
import { useFormData } from '@/pages/main/main01/main01Logic.js'
import { FORM_DEFAULTS } from '@/pages/main/main01/main01Constants.js'

export default {
    setup() {
        const {
            formData,
            loadFormData,
            resetForm,
            submitForm,
            updateFormField
        } = useFormData()

        return {
            formData,
            FORM_DEFAULTS,
            // 方法
            loadFormData,
            resetForm,
            submitForm,
            updateFormField
        }
    },
    methods: {
        formSubmit(e) {
            this.submitForm(e.detail.value)
        },
        formReset() {
            this.resetForm()
        },
        onSwitchChange(e) {
            this.updateFormField('switch', e.detail.value)
        },
        onRadioChange(e) {
            this.updateFormField('radio', e.detail.value)
        },
        onCheckboxChange(e) {
            this.updateFormField('checkbox', e.detail.value)
        },
        onSliderChange(e) {
            this.updateFormField('slider', e.detail.value)
        },
        onInputChange(e) {
            this.updateFormField('input', e.detail.value)
        }
    },
    async onLoad(option) {
        await this.loadFormData(option)
        console.log('页面接收到的参数：', option)
    }
}
</script>
<style>
.uni-form-item .title {
    padding: 20rpx 0;
}
</style>
