import autoprefixer from 'autoprefixer';
import type { Config } from 'postcss-load-config';
import tailwindcss from 'tailwindcss';

const config: Config = {
	plugins: [tailwindcss({ config: './tailwind.config.ts' }), autoprefixer()],
};

export default config;
