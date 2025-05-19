import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { authApi } from '../services/api';

const ForgotPasswordPage: React.FC = () => {
	const [email, setEmail] = useState('');
	const [message, setMessage] = useState<string | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(false);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		setMessage(null);
		setIsLoading(true);
		try {
			await authApi.requestPasswordReset(email);
			setMessage('If your email is registered, you will receive a reset link.');
		} catch (err: unknown) {
			if (err instanceof Error) {
				setError(err.message || 'Failed to request password reset.');
			} else {
				setError('An unexpected error occurred.');
			}
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<div className='min-h-screen flex items-center justify-center bg-gray-100 py-12 px-4 sm:px-6 lg:px-8'>
			<div className='max-w-md w-full space-y-8 bg-white p-8 rounded-lg shadow-md'>
				<div>
					<h2 className='mt-6 text-center text-3xl font-extrabold text-gray-900'>
						Forgot your password?
					</h2>
					<p className='mt-2 text-center text-sm text-gray-600'>
						Enter your email and we'll send you a reset link.
					</p>
				</div>
				<form className='mt-8 space-y-6' onSubmit={handleSubmit}>
					{error && (
						<div
							className='bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative'
							role='alert'
						>
							<span className='block sm:inline'>{error}</span>
						</div>
					)}
					{message && (
						<div
							className='bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative'
							role='alert'
						>
							<span className='block sm:inline'>{message}</span>
						</div>
					)}
					<div className='rounded-md shadow-sm -space-y-px'>
						<div>
							<label htmlFor='email' className='sr-only'>
								Email address
							</label>
							<input
								id='email'
								name='email'
								type='email'
								required
								className='appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-primary-500 focus:border-primary-500 focus:z-10 sm:text-sm'
								placeholder='Email address'
								value={email}
								onChange={(e) => setEmail(e.target.value)}
							/>
						</div>
					</div>
					<div>
						<button
							type='submit'
							disabled={isLoading}
							className={`group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white ${
								isLoading
									? 'bg-primary-400 cursor-not-allowed'
									: 'bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500'
							}`}
						>
							{isLoading ? 'Sending...' : 'Send reset link'}
						</button>
					</div>
				</form>
				<p className='mt-2 text-center text-sm text-gray-600'>
					<Link to='/login' className='font-medium text-primary-600 hover:text-primary-500'>
						Back to login
					</Link>
				</p>
			</div>
		</div>
	);
};

export default ForgotPasswordPage;
