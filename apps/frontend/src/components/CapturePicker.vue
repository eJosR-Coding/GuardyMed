<script setup>
import { nextTick, onBeforeUnmount, ref } from "vue";
import Icon from "./Icon.vue";
import { notify } from "../store";

const props = defineProps({
  cv: { type: Object, required: true }, // GET /attendance/cv/status
  mode: { type: String, required: true }, // "enroll" | "verify"
  busy: Boolean,
});
const emit = defineEmits(["capture"]);

const video = ref(null);
const stream = ref(null);
const fileInput = ref(null);

const demoChoices = () => props.cv.demo_captures.filter((c) => (props.mode === "enroll" ? c.id === "enroll" : c.id !== "enroll"));

async function startCamera() {
  try {
    stream.value = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
    await nextTick();
    video.value.srcObject = stream.value;
  } catch {
    notify("The camera is not available. You can upload a photo instead.", "error");
  }
}

function stopCamera() {
  stream.value?.getTracks().forEach((track) => track.stop());
  stream.value = null;
}

function snapshot() {
  const source = video.value;
  const scale = Math.min(1, 800 / (source.videoWidth || 800));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(source.videoWidth * scale);
  canvas.height = Math.round(source.videoHeight * scale);
  canvas.getContext("2d").drawImage(source, 0, 0, canvas.width, canvas.height);
  stopCamera();
  emit("capture", canvas.toDataURL("image/jpeg", 0.9).split(",")[1]);
}

function onFile(event) {
  const file = event.target.files?.[0];
  event.target.value = "";
  if (!file) return;
  if (file.size > 4 * 1024 * 1024) return notify("Choose an image under 4 MB.", "error");
  const reader = new FileReader();
  reader.onload = () => emit("capture", String(reader.result).split(",")[1]);
  reader.readAsDataURL(file);
}

onBeforeUnmount(stopCamera);
</script>

<template>
  <div class="stack">
    <div v-if="cv.is_demo" class="banner banner-warn">
      <Icon name="info" />
      <div>
        <strong>Demo runtime, not real face recognition.</strong>
        <span v-if="cv.fallback_reason"> The real model could not start, so GuardyMed fell back to the demo runtime.</span>
        Pick a simulated capture below to see each outcome. A real photo is only compared byte-for-byte.
      </div>
    </div>

    <div v-if="cv.is_demo" class="choice-grid">
      <button v-for="choice in demoChoices()" :key="choice.id" class="choice" type="button" :disabled="busy" @click="emit('capture', choice.media_base64)">
        <span>{{ choice.label }}</span>
        <Icon name="chevron" />
      </button>
    </div>

    <component :is="cv.is_demo ? 'details' : 'div'" class="stack">
      <summary v-if="cv.is_demo" class="muted" style="cursor: pointer">Use a camera or photo instead</summary>
      <div v-if="stream" class="stack">
        <div class="camera"><video ref="video" autoplay playsinline muted /></div>
        <div class="row">
          <button class="btn btn-primary" type="button" :disabled="busy" @click="snapshot"><Icon name="camera" /> Take photo</button>
          <button class="btn" type="button" @click="stopCamera">Cancel</button>
        </div>
      </div>
      <div v-else class="row" style="margin-top: 12px">
        <button class="btn" type="button" :disabled="busy" @click="startCamera"><Icon name="camera" /> Use camera</button>
        <button class="btn" type="button" :disabled="busy" @click="fileInput.click()"><Icon name="upload" /> Upload photo</button>
        <input ref="fileInput" type="file" accept="image/*" class="sr-only" tabindex="-1" @change="onFile" />
      </div>
      <p class="hint" style="margin-top: 8px">Photos are used once to compute a face template and are not stored.</p>
    </component>
  </div>
</template>
