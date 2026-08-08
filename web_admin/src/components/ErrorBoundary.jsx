import React, { Component } from 'react';
import ErrorPage from '../pages/ErrorPage';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error('[GLOBAL ERROR BOUNDARY CAUGHT EXCEPTION]:', error, errorInfo);
  }

  resetErrorBoundary = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen app-bg-gradient flex items-center justify-center p-6">
          <ErrorPage 
            error={this.state.error} 
            errorInfo={this.state.errorInfo} 
            resetErrorBoundary={this.resetErrorBoundary}
          />
        </div>
      );
    }

    return this.props.children;
  }
}
