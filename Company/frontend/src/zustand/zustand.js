import { tabClasses } from '@mui/material'
import { create } from 'zustand'

export const useGlobalStore = create((set) => ({
    pageNumber: -1,
    setPageNumber: (pageNumber) => set({ pageNumber }),
    tabSelected: -1,
    setTabSelected: (tabSelected) => set({ tabSelected }),
}))
