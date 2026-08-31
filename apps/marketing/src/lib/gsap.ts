/**
 * Single place GSAP is imported and configured. Sections should import
 * `gsap` and `ScrollTrigger` from here rather than from the `gsap` package
 * directly, so the plugin registration below always runs first.
 */
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export { gsap, ScrollTrigger }
