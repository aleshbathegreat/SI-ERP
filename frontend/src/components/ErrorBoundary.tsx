"use client";

import { Component, ErrorInfo, ReactNode } from "react";
import { Alert, AlertTitle, Box, Button, Stack, Typography } from "@mui/material";

type Props = { children: ReactNode; title?: string };
type State = { error: Error | null };

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Module crash:", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <Box sx={{ p: 3, maxWidth: 720 }}>
        <Alert
          severity="error"
          action={
            <Stack direction="row" spacing={1}>
              <Button color="inherit" size="small" onClick={() => window.history.back()}>
                Back
              </Button>
              <Button color="inherit" size="small" onClick={() => this.setState({ error: null })}>
                Try again
              </Button>
              <Button color="inherit" size="small" onClick={() => window.location.reload()}>
                Reload
              </Button>
            </Stack>
          }
        >
          <AlertTitle>{this.props.title || "This page couldn’t load"}</AlertTitle>
          <Typography variant="body2" sx={{ mt: 1, fontFamily: "monospace" }}>
            {this.state.error.message}
          </Typography>
        </Alert>
      </Box>
    );
  }
}
