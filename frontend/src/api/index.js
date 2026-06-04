import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (res) => {
    return res.data
  },
  (err) => {
    const status = err.response?.status
    if (status === 401 || status === 422) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    if (err.config?.responseType === 'blob' && err.response?.data) {
      return Promise.reject({ isBlob: true, data: err.response.data, status })
    }
    return Promise.reject(err.response?.data || err)
  },
)

export const authAPI = {
  login: (d) => http.post('/auth/login', d),
  register: (d) => http.post('/auth/register', d),
  sendCode: (d) => http.post('/auth/send-code', d),
  resetPassword: (d) => http.post('/auth/reset-password', d),
  changePassword: (d) => http.put('/auth/change-password', d),
}

export const analysisAPI = {
  upload: (form) => http.post('/upload', form),
  getResult: (tid) => http.get(`/analyze?task_id=${tid}`),
  save: (tid, data = {}) => http.post('/save', { task_id: tid, ...data }),
  exportPdf: (data) => http.post('/export-pdf', data, { responseType: 'blob' }),
  batchUpload: (form) => http.post('/batch-upload', form),
  getBatchResults: (taskIds) => http.get(`/batch-results?task_ids=${taskIds.join(',')}`),
}

export const historyAPI = {
  list: () => http.get('/history'),
  trend: (p) => http.get('/history/trend', { params: p }),
  export: (p) => http.get('/history/export', { params: p, responseType: 'blob' }),
  exportPdf: (p) => http.get('/history/export-pdf', { params: p, responseType: 'blob' }),
  quickAdd: (d) => http.post('/history/quick-add', d),
}

export const foodsAPI = {
  list: (p) => http.get('/foods', { params: p }),
  detail: (id) => http.get(`/foods/${id}`),
  recommend: () => http.get('/foods', { params: { recommend: 1, per_page: 8 } }),
  create: (d) => http.post('/foods', d),
  update: (id, d) => http.put(`/foods/${id}`, d),
  remove: (id) => http.delete(`/foods/${id}`),
  myFoods: (p) => http.get('/my-foods', { params: p }),
}

export const categoriesAPI = {
  list: () => http.get('/categories'),
  create: (d) => http.post('/categories', d),
  update: (id, d) => http.put(`/categories/${id}`, d),
  remove: (id) => http.delete(`/categories/${id}`),
}

export const usersAPI = {
  list: (p) => http.get('/users', { params: p }),
  detail: (id) => http.get(`/users/${id}`),
  update: (id, d) => http.put(`/users/${id}`, d),
  remove: (id) => http.delete(`/users/${id}`),
  resetPassword: (id, d) => http.put(`/users/${id}/reset-password`, d),
  getProfile: () => http.get('/profile'),
  updateProfile: (d) => http.put('/profile', d),
}

export const dietAPI = {
  list: (p) => http.get('/diet-records', { params: p }),
  summary: (d) => http.get('/diet-records/summary', { params: { date: d } }),
  add: (d) => http.post('/diet-records', d),
  update: (id, d) => http.put(`/diet-records/${id}`, d),
  remove: (id) => http.delete(`/diet-records/${id}`),
  batchAdd: (d) => http.post('/diet-records/batch', d),
  suggestions: (d) => http.get('/diet-records/suggestions', { params: { date: d } }),
}

export const assessAPI = {
  list: (p) => http.get('/assessments', { params: p }),
  myLast: () => http.get('/assessments/me'),
  add: (d) => http.post('/assessments', d),
  remove: (id) => http.delete(`/assessments/${id}`),
}

