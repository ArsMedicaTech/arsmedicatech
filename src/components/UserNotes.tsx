// UserNotes
import { MDXEditor } from '@mdxeditor/editor';
import '@mdxeditor/editor/style.css';
import React, { useEffect, useState } from 'react';
import { userNotesAPI } from '../services/api';

// Import all the plugins we need
import {
  BoldItalicUnderlineToggles,
  CreateLink,
  InsertImage,
  InsertTable,
  ListsToggle,
  UndoRedo,
  codeBlockPlugin,
  codeMirrorPlugin,
  diffSourcePlugin,
  frontmatterPlugin,
  headingsPlugin,
  imagePlugin,
  linkDialogPlugin,
  linkPlugin,
  listsPlugin,
  markdownShortcutPlugin,
  quotePlugin,
  sandpackPlugin,
  tablePlugin,
  thematicBreakPlugin,
  toolbarPlugin,
} from '@mdxeditor/editor';

interface UserNote {
  id: string;
  title: string;
  content: string;
  note_type: 'private' | 'shared';
  tags: string[];
  date_created: string;
  date_updated: string;
}

interface UserNotesTableProps {
  children: React.ReactNode;
}

const UserNotesTable: React.FC<UserNotesTableProps> = ({ children }) => {
  return <div className="bg-white rounded-lg shadow-md p-6">{children}</div>;
};

const UserNotes: React.FC<{
  note?: UserNote;
  onSave?: (note: UserNote) => void;
}> = ({ note, onSave }) => {
  const [markdown, setMarkdown] = useState(note?.content || '');
  const [title, setTitle] = useState(note?.title || '');
  const [noteType, setNoteType] = useState<'private' | 'shared'>(
    note?.note_type || 'private'
  );
  const [tags, setTags] = useState<string[]>(note?.tags || []);
  const [isEditing, setIsEditing] = useState(!note);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    if (!title.trim()) {
      alert('Please enter a title for the note');
      return;
    }

    if (!markdown.trim()) {
      alert('Please enter some content for the note');
      return;
    }

    setIsSaving(true);
    try {
      const noteData = {
        title: title.trim(),
        content: markdown,
        note_type: noteType,
        tags: tags,
      };

      let savedNote: UserNote;

      if (note?.id) {
        // Update existing note
        const response = await userNotesAPI.update(note.id, noteData);
        if (response.success) {
          savedNote = response.note;
        } else {
          throw new Error(response.error || 'Failed to update note');
        }
      } else {
        // Create new note
        const response = await userNotesAPI.create(noteData);
        if (response.success) {
          savedNote = response.note;
        } else {
          throw new Error(response.error || 'Failed to create note');
        }
      }

      if (onSave) {
        onSave(savedNote);
      }
    } catch (error) {
      console.error('Error saving note:', error);
      console.error('Error saving note:', error);
      alert('An error occurred while saving the note. Please try again later.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-4">
        <div className="flex-1 mr-4">
          <input
            type="text"
            placeholder="Note title..."
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-xl font-semibold"
            disabled={!isEditing}
          />
        </div>
        <div className="flex space-x-2">
          {isEditing && (
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:bg-blue-400"
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          )}
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
          >
            {isEditing ? 'View' : 'Edit'}
          </button>
        </div>
      </div>

      {isEditing && (
        <div className="mb-4 flex space-x-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Type:</label>
            <select
              value={noteType}
              onChange={e =>
                setNoteType(e.target.value as 'private' | 'shared')
              }
              className="px-3 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="private">Private</option>
              <option value="shared">Shared</option>
            </select>
          </div>
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Tags:</label>
            <input
              type="text"
              placeholder="tag1, tag2, tag3..."
              value={tags.join(', ')}
              onChange={e =>
                setTags(
                  e.target.value
                    .split(',')
                    .map(tag => tag.trim())
                    .filter(tag => tag)
                )
              }
              className="px-3 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      )}

      <MDXEditor
        markdown={markdown}
        onChange={setMarkdown}
        readOnly={!isEditing}
        className="min-h-[400px] border border-gray-300 rounded-lg"
        contentEditableClassName="prose max-w-none p-4 text-left"
        plugins={[
          headingsPlugin(),
          listsPlugin(),
          quotePlugin(),
          thematicBreakPlugin(),
          markdownShortcutPlugin(),
          linkPlugin(),
          linkDialogPlugin(),
          imagePlugin(),
          tablePlugin(),
          codeBlockPlugin(),
          codeMirrorPlugin({
            codeBlockLanguages: { js: 'JavaScript', css: 'CSS', txt: 'text' },
          }),
          sandpackPlugin(),
          frontmatterPlugin(),
          diffSourcePlugin(),
          toolbarPlugin({
            toolbarContents: () => (
              <>
                <UndoRedo />
                <BoldItalicUnderlineToggles />
                <ListsToggle />
                <CreateLink />
                <InsertImage />
                <InsertTable />
              </>
            ),
          }),
        ]}
      />
    </div>
  );
};

const UserNotesScreen: React.FC = () => {
  const [notes, setNotes] = useState<UserNote[]>([]);
  const [selectedNote, setSelectedNote] = useState<UserNote | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewNote, setShowNewNote] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadNotes();
  }, []);

  const loadNotes = async () => {
    try {
      setIsLoading(true);
      const response = await userNotesAPI.getAll();
      if (response.success) {
        setNotes(response.notes);
      } else {
        setError('Failed to load notes');
      }
    } catch (err) {
      setError('Error loading notes');
      console.error('Error loading notes:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNoteClick = (note: UserNote) => {
    setSelectedNote(note);
    setShowNewNote(false);
  };

  const handleNewNote = () => {
    setSelectedNote(null);
    setShowNewNote(true);
  };

  const handleSaveNote = async (note: UserNote) => {
    try {
      if (note.id) {
        // Update existing note - only send the fields to update, not the entire note object
        const updateData = {
          title: note.title,
          content: note.content,
          note_type: note.note_type,
          tags: note.tags,
        };
        const response = await userNotesAPI.update(note.id, updateData);
        if (response.success) {
          setNotes(notes.map(n => (n.id === note.id ? response.note : n)));
          setSelectedNote(response.note);
        }
      } else {
        // Create new note
        const response = await userNotesAPI.create(note);
        if (response.success) {
          setNotes([response.note, ...notes]);
          setSelectedNote(response.note);
          setShowNewNote(false);
        }
      }
    } catch (err) {
      setError('Error saving note');
      console.error('Error saving note:', err);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!confirm('Are you sure you want to delete this note?')) return;

    try {
      const response = await userNotesAPI.delete(noteId);
      if (response.success) {
        setNotes(notes.filter(n => n.id !== noteId));
        if (selectedNote?.id === noteId) {
          setSelectedNote(null);
        }
      }
    } catch (err) {
      setError('Error deleting note');
      console.error('Error deleting note:', err);
    }
  };

  const filteredNotes = notes.filter(
    note =>
      note.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      note.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      note.tags.some(tag =>
        tag.toLowerCase().includes(searchQuery.toLowerCase())
      )
  );

  return (
    <div className="flex h-full">
      {/* Notes List */}
      <div className="w-1/3 border-r border-gray-200 p-4">
        <div className="mb-4">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-2xl font-bold text-gray-800">My Notes</h1>
            <button
              onClick={handleNewNote}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
            >
              New Note
            </button>
          </div>

          <input
            type="text"
            placeholder="Search notes..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {isLoading ? (
          <div className="text-center py-8">Loading notes...</div>
        ) : error ? (
          <div className="text-red-600 py-8">{error}</div>
        ) : (
          <div className="space-y-2">
            {filteredNotes.map(note => (
              <div
                key={note.id}
                onClick={() => handleNoteClick(note)}
                className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                  selectedNote?.id === note.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-800 truncate">
                      {note.title}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {new Date(note.date_updated).toLocaleDateString()}
                    </p>
                    <div className="flex items-center mt-2 space-x-2">
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          note.note_type === 'private'
                            ? 'bg-gray-100 text-gray-700'
                            : 'bg-green-100 text-green-700'
                        }`}
                      >
                        {note.note_type}
                      </span>
                      {note.tags.map((tag, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      handleDeleteNote(note.id);
                    }}
                    className="text-red-600 hover:text-red-800 ml-2"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Note Editor/Viewer */}
      <div className="flex-1 p-4">
        {showNewNote ? (
          <UserNotes onSave={handleSaveNote} />
        ) : selectedNote ? (
          <UserNotes note={selectedNote} onSave={handleSaveNote} />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <svg
                className="w-16 h-16 mx-auto mb-4 text-gray-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p className="text-lg">
                Select a note to view or create a new one
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserNotesScreen;
