// The words of each SearchPicker in the app, in one place. In a form, `all` is the prompt
// ("Choose a building") or the empty choice of an optional field ("No owner"); in a filter it is
// the "All …" choice and `clear` names the × button.
import type { PickerWords } from '../components/list/SearchPicker.vue'

export const FIELD_WORDS = {
  office: { all: 'Choose an office', search: 'Search offices', unknown: 'Unknown office', none: 'No office matches' },
  building: { all: 'Choose a building', search: 'Search buildings', unknown: 'Unknown building', none: 'No building matches' },
  floor: { all: 'Choose a floor', search: 'Search floors', unknown: 'Unknown floor', none: 'No floor matches' },
  roomType: { all: 'Choose a room type', search: 'Search room types', unknown: 'Unknown room type', none: 'No room type matches' },
  owner: { all: 'No owner', search: 'Search people', unknown: 'Unknown owner', none: 'No one matches' },
  province: { all: 'Choose a province', search: 'Search provinces', unknown: 'Unknown province', none: 'No province matches' },
  department: { all: 'Choose a department', search: 'Search departments', unknown: 'Unknown department', none: 'No department matches' },
} satisfies Record<string, PickerWords>

export const FILTER_WORDS = {
  office: { all: 'All offices', search: 'Search offices', unknown: 'Unknown office', none: 'No office matches', clear: 'Show all offices' },
  building: { all: 'All buildings', search: 'Search buildings', unknown: 'Unknown building', none: 'No building matches', clear: 'Show all buildings' },
  floor: { all: 'All floors', search: 'Search floors', unknown: 'Unknown floor', none: 'No floor matches', clear: 'Show all floors' },
  roomType: { all: 'All types', search: 'Search room types', unknown: 'Unknown room type', none: 'No room type matches', clear: 'Show all types' },
  owner: { all: 'Any owner', search: 'Search people', unknown: 'Unknown owner', none: 'No one matches', clear: 'Show any owner' },
  province: { all: 'All provinces', search: 'Search provinces', unknown: 'Unknown province', none: 'No province matches', clear: 'Show all provinces' },
  department: { all: 'All departments', search: 'Search departments', unknown: 'Unknown department', none: 'No department matches', clear: 'Show all departments' },
} satisfies Record<string, PickerWords>
