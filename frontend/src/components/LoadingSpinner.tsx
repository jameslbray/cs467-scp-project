import React from 'react';

interface LoadingSpinnerProps {
	message?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ message }) => (
	<div className='flex flex-col items-center justify-center min-h-[120px]'>
		<div className='animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500 border-solid mb-2' />
		{message && <span className='text-gray-600 dark:text-gray-300'>{message}</span>}
	</div>
);

export default LoadingSpinner;
