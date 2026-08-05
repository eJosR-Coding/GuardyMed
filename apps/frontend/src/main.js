import { createApp } from "vue";
import PrimeVue from "primevue/config";
import ToastService from "primevue/toastservice";
import Select from "primevue/select";
import InputNumber from "primevue/inputnumber";
import Tag from "primevue/tag";
import Toast from "primevue/toast";
import App from "./App.vue";
import { GuardyMedPreset } from "./core/theme/preset";
import "primeicons/primeicons.css";
import "./core/styles/app.css";

const app = createApp(App);

app.use(PrimeVue, {
  theme: {
    preset: GuardyMedPreset,
    options: {
      darkModeSelector: false,
      cssLayer: false,
    },
  },
});
app.use(ToastService);

app.component("PSelect", Select);
app.component("PInputNumber", InputNumber);
app.component("PTag", Tag);
app.component("PToast", Toast);

app.mount("#app");
