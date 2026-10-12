import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('fin_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (resp) => resp.data,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail || '请求失败，请稍后重试'
    if (status === 401) {
      localStorage.removeItem('fin_token')
      localStorage.removeItem('fin_user')
      if (router.currentRoute.value.name !== 'login') {
        ElMessage.warning('登录已失效，请重新登录')
        router.push('/login')
      }
    } else {
      // detail 可能是 FastAPI 校验错误数组
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg).join('；')
        : String(detail)
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
)

export default api
