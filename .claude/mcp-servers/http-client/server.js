#!/usr/bin/env node

/**
 * HTTP Client MCP Server - v1.0
 * 
 * A comprehensive HTTP client server for making requests with all HTTP methods.
 * Supports GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS and custom methods.
 * 
 * Key Features:
 * - Universal HTTP request tool supporting all methods
 * - Simplified GET and POST convenience methods
 * - Configurable default headers
 * - Request/response body handling with multiple content types
 * - Comprehensive error handling and response details
 * - Support for query parameters, custom headers, and authentication
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';

class HttpClientServer {
  constructor() {
    this.server = new Server(
      {
        name: 'http-client-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.defaultHeaders = {
      'User-Agent': 'MCP-HTTP-Client/1.0'
    };

    this.setupToolHandlers();
    
    // Error handling
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'http_request',
          description: 'Make HTTP requests with any method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, etc.). Supports custom headers, query parameters, request body, and authentication. Returns complete response details including status, headers, and body.',
          inputSchema: {
            type: 'object',
            properties: {
              url: {
                type: 'string',
                description: 'The URL to make the request to (must include protocol: http:// or https://)'
              },
              method: {
                type: 'string',
                enum: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'CONNECT', 'TRACE'],
                default: 'GET',
                description: 'HTTP method to use'
              },
              headers: {
                type: 'object',
                description: 'Custom headers to include in the request',
                additionalProperties: { type: 'string' }
              },
              body: {
                type: 'string',
                description: 'Request body (for POST, PUT, PATCH requests). Can be JSON string, form data, or plain text'
              },
              query_params: {
                type: 'object',
                description: 'Query parameters to append to URL',
                additionalProperties: { type: 'string' }
              },
              timeout: {
                type: 'integer',
                default: 30000,
                description: 'Request timeout in milliseconds (default: 30000)'
              },
              follow_redirects: {
                type: 'boolean',
                default: true,
                description: 'Whether to follow HTTP redirects'
              }
            },
            required: ['url']
          }
        },
        {
          name: 'http_get',
          description: 'Simplified GET request method. Perfect for fetching data from APIs, web pages, or any HTTP endpoint. Automatically handles JSON responses and provides clean error messages.',
          inputSchema: {
            type: 'object',
            properties: {
              url: {
                type: 'string',
                description: 'The URL to fetch (must include protocol: http:// or https://)'
              },
              headers: {
                type: 'object',
                description: 'Additional headers to include',
                additionalProperties: { type: 'string' }
              },
              query_params: {
                type: 'object',
                description: 'Query parameters to append to URL',
                additionalProperties: { type: 'string' }
              }
            },
            required: ['url']
          }
        },
        {
          name: 'http_post',
          description: 'Simplified POST request method for sending data to servers. Supports JSON data, form submissions, and file uploads. Automatically sets appropriate Content-Type headers.',
          inputSchema: {
            type: 'object',
            properties: {
              url: {
                type: 'string',
                description: 'The URL to post to (must include protocol: http:// or https://)'
              },
              data: {
                type: 'string',
                description: 'Data to send in request body. For JSON, pass stringified JSON. For forms, use URL-encoded string.'
              },
              content_type: {
                type: 'string',
                enum: ['application/json', 'application/x-www-form-urlencoded', 'text/plain', 'application/xml'],
                default: 'application/json',
                description: 'Content type of the request body'
              },
              headers: {
                type: 'object',
                description: 'Additional headers to include',
                additionalProperties: { type: 'string' }
              }
            },
            required: ['url', 'data']
          }
        },
        {
          name: 'set_default_headers',
          description: 'Configure default headers that will be included in all subsequent HTTP requests. Useful for setting API keys, authentication tokens, or standard headers like User-Agent.',
          inputSchema: {
            type: 'object',
            properties: {
              headers: {
                type: 'object',
                description: 'Headers to set as defaults for all requests',
                additionalProperties: { type: 'string' }
              },
              merge: {
                type: 'boolean',
                default: true,
                description: 'Whether to merge with existing defaults (true) or replace them (false)'
              }
            },
            required: ['headers']
          }
        }
      ]
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'http_request':
            return await this.handleHttpRequest(args);
          case 'http_get':
            return await this.handleHttpGet(args);
          case 'http_post':
            return await this.handleHttpPost(args);
          case 'set_default_headers':
            return await this.handleSetDefaultHeaders(args);
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${name}`
            );
        }
      } catch (error) {
        if (error instanceof McpError) {
          throw error;
        }
        throw new McpError(
          ErrorCode.InternalError,
          `Tool execution failed: ${error.message}`
        );
      }
    });
  }

  buildUrl(baseUrl, queryParams) {
    if (!queryParams || Object.keys(queryParams).length === 0) {
      return baseUrl;
    }
    
    const url = new URL(baseUrl);
    Object.entries(queryParams).forEach(([key, value]) => {
      url.searchParams.append(key, value);
    });
    return url.toString();
  }

  async handleHttpRequest(args) {
    const {
      url,
      method = 'GET',
      headers = {},
      body,
      query_params,
      timeout = 30000,
      follow_redirects = true
    } = args;

    if (!url) {
      throw new McpError(ErrorCode.InvalidParams, 'URL is required');
    }

    try {
      const finalUrl = this.buildUrl(url, query_params);
      const finalHeaders = { ...this.defaultHeaders, ...headers };

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const fetchOptions = {
        method: method.toUpperCase(),
        headers: finalHeaders,
        signal: controller.signal,
        redirect: follow_redirects ? 'follow' : 'manual'
      };

      if (body && ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase())) {
        fetchOptions.body = body;
      }

      const response = await fetch(finalUrl, fetchOptions);
      clearTimeout(timeoutId);

      const responseHeaders = Object.fromEntries(response.headers.entries());
      let responseBody;

      try {
        const text = await response.text();
        try {
          responseBody = JSON.parse(text);
        } catch {
          responseBody = text;
        }
      } catch (error) {
        responseBody = 'Failed to read response body';
      }

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            success: true,
            status: response.status,
            statusText: response.statusText,
            headers: responseHeaders,
            body: responseBody,
            url: response.url,
            redirected: response.redirected
          }, null, 2)
        }]
      };

    } catch (error) {
      if (error.name === 'AbortError') {
        throw new McpError(ErrorCode.InternalError, `Request timed out after ${timeout}ms`);
      }
      
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            success: false,
            error: error.message,
            type: error.name,
            url: url
          }, null, 2)
        }]
      };
    }
  }

  async handleHttpGet(args) {
    return await this.handleHttpRequest({
      ...args,
      method: 'GET'
    });
  }

  async handleHttpPost(args) {
    const { url, data, content_type = 'application/json', headers = {} } = args;

    if (!data) {
      throw new McpError(ErrorCode.InvalidParams, 'Data is required for POST requests');
    }

    const finalHeaders = {
      'Content-Type': content_type,
      ...headers
    };

    return await this.handleHttpRequest({
      url,
      method: 'POST',
      headers: finalHeaders,
      body: data
    });
  }

  async handleSetDefaultHeaders(args) {
    const { headers, merge = true } = args;

    if (!headers || typeof headers !== 'object') {
      throw new McpError(ErrorCode.InvalidParams, 'Headers object is required');
    }

    if (merge) {
      this.defaultHeaders = { ...this.defaultHeaders, ...headers };
    } else {
      this.defaultHeaders = { ...headers };
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          message: 'Default headers updated',
          current_defaults: this.defaultHeaders
        }, null, 2)
      }]
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('HTTP Client MCP server running on stdio');
  }
}

const server = new HttpClientServer();
server.run().catch(console.error);