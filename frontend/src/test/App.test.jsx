import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import App from '../App';

describe('App', () => {
    it('renders navigation links', async () => {
        render(
            <BrowserRouter>
                <App />
            </BrowserRouter>
        );

        expect(screen.getByText(/Parking AI/i)).toBeInTheDocument();
        expect(screen.getByText(/Início/i)).toBeInTheDocument();
    });
});
