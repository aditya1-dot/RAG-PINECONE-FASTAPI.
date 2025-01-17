# RAG-PINECONE-FASTAPI.
A Streamlit-based web application that enables users to upload PDF documents and interact with them using natural language queries powered by RAG (Retrieval-Augmented Generation). The app integrates a secure user authentication system, session management, and a FastAPI backend for seamless document processing and querying.

Features

User Authentication: Secure login system with session management.

PDF Document Upload: Support for single or multiple PDF file uploads.

Interactive Chat Interface: Chat with your uploaded documents using natural language queries.

Session Management: Persistent user sessions with chat history.

Responsive UI: Clean and intuitive user interface with sidebar navigation.

System Architecture

The application consists of two main components:

Frontend (Streamlit)

Provides the user interface and handles user interactions.

Manages file uploads and chat sessions.

Handles session management and displays chat history.

Backend (FastAPI)

Handles document processing and storage.

Provides query processing using RAG.

Offers API endpoints for document ingestion and querying.

