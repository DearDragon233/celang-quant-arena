import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('fin_token') || '',
    user: JSON.parse(localStorage.getItem('fin_user') || 'null'),
    contest: JSON.parse(localStorage.getItem('fin_contest') || 'null'),
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === 'admin',
  },
  actions: {
    setSession(token, user) {
      this.token = token
      this.user = user
      localStorage.setItem('fin_token', token)
      localStorage.setItem('fin_user', JSON.stringify(user))
    },
    setContest(contest) {
      this.contest = contest
      if (contest) localStorage.setItem('fin_contest', JSON.stringify(contest))
      else localStorage.removeItem('fin_contest')
    },
    logout() {
      this.setContest(null)
      this.token = ''
      this.user = null
      localStorage.removeItem('fin_token')
      localStorage.removeItem('fin_user')
    },
  },
})
