"""Durable, venture-scoped documents with immutable revision history.

These records are independent of task workspaces. This service grants no file or
provider permissions; callers must supply the authenticated actor themselves.
"""
from copy import deepcopy
from pathlib import Path
import re

from .store import ident, now


KINDS = {'reference', 'proposal', 'design', 'review', 'decisions'}
FIELDS = {'name', 'kind', 'content', 'read_only'}


class VentureDocuments:
    def __init__(self, store, root=None):
        self.store = store
        # Accepted for embedding compatibility; content always lives in SQLite.
        self.root = Path(root) if root is not None else None

    def _venture(self, venture_id):
        if not isinstance(venture_id, str) or not self.store.get('ventures', venture_id):
            raise ValueError('Unknown venture')

    @staticmethod
    def _actor(actor):
        if not isinstance(actor, str) or not actor.strip() or len(actor) > 300:
            raise ValueError('Invalid document actor')
        return actor

    @staticmethod
    def _validate(body, updating=False):
        if not isinstance(body, dict):
            raise ValueError('Document must be an object')
        allowed = FIELDS | ({'expected_revision'} if updating else set())
        if set(body) - allowed:
            raise ValueError('Unsupported document fields')
        if 'name' in body:
            name = body['name']
            if (not isinstance(name, str) or not 1 <= len(name) <= 200
                    or name != name.strip() or name.endswith('.')
                    or re.search(r'[\x00-\x1f\x7f<>:"/\\|?*]', name)
                    or name in {'.', '..'}
                    or Path(name).suffix.lower() not in {'.md', '.txt'}
                    or name.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                        *{'COM' + str(i) for i in range(1, 10)},
                        *{'LPT' + str(i) for i in range(1, 10)}}):
                raise ValueError('Document name must be a safe .md or .txt basename')
        if 'kind' in body and (not isinstance(body['kind'], str) or body['kind'] not in KINDS):
            raise ValueError('Invalid document kind')
        if 'content' in body and (not isinstance(body['content'], str) or len(body['content']) > 200000):
            raise ValueError('Document content must contain at most 200000 characters')
        if 'read_only' in body and not isinstance(body['read_only'], bool):
            raise ValueError('read_only must be a boolean')
        if updating and (type(body.get('expected_revision')) is not int or body['expected_revision'] < 1):
            raise ValueError('expected_revision is required and must be a positive integer')
        return deepcopy(body)

    def _unique(self, venture_id, name, except_id=None):
        if any(d['venture_id'] == venture_id and d['name'].casefold() == name.casefold()
               and d['id'] != except_id for d in self.store.all('venture_documents')):
            raise ValueError('A document with this name already exists in this venture')

    def _save(self, document, actor, action):
        revision = dict(id=ident(), document_id=document['id'],
                        venture_id=document['venture_id'], version=document['version'],
                        revision=document['version'], actor=actor,
                        created_at=document['updated_at'], document=deepcopy(document))
        event = dict(id=ident(), action=action, venture_id=document['venture_id'],
                     document_id=document['id'], version=document['version'],
                     actor=actor, created_at=document['updated_at'])
        self.store.batch([('venture_documents', document),
                          ('venture_document_revisions', revision)], [event])
        return deepcopy(document)

    def create(self, venture_id, body, actor='ceo'):
        body = self._validate(body)
        actor = self._actor(actor)
        if not {'name', 'content'} <= set(body):
            raise ValueError('Document name and content are required')
        kind = body.get('kind', 'reference')
        if actor != 'ceo' and kind == 'decisions':
            raise PermissionError('Decision documents require CEO approval')
        with self.store.lock:
            self._venture(venture_id)
            self._unique(venture_id, body['name'])
            timestamp = now()
            document = dict(id=ident(), venture_id=venture_id,
                            name=body['name'], content=body['content'], kind=kind,
                            read_only=body.get('read_only', kind in {'reference', 'decisions'}),
                            version=1, revision=1, created_at=timestamp, updated_at=timestamp,
                            created_by=actor, updated_by=actor)
            return self._save(document, actor, 'venture_document_created')

    def update(self, venture_id, doc_id, body, actor='ceo'):
        body = self._validate(body, updating=True)
        actor = self._actor(actor)
        with self.store.lock:
            document = self.get(venture_id, doc_id)
            if actor != 'ceo' and (document['read_only'] or document['kind'] == 'decisions'
                    or body.get('kind') == 'decisions' or 'read_only' in body):
                raise PermissionError('Only the CEO can revise locked or decision documents and locks')
            if body['expected_revision'] != document['version']:
                raise ValueError('Stale document revision; reload before updating')
            document.update({key: value for key, value in body.items() if key in FIELDS})
            self._unique(venture_id, document['name'], doc_id)
            document.update(version=document['version'] + 1,
                            revision=document['version'] + 1,
                            updated_at=now(), updated_by=actor)
            return self._save(document, actor, 'venture_document_revised')

    def list(self, venture_id):
        self._venture(venture_id)
        return [d for d in self.store.all('venture_documents') if d['venture_id'] == venture_id]

    def get(self, venture_id, doc_id):
        self._venture(venture_id)
        document = self.store.get('venture_documents', doc_id)
        if not document or document['venture_id'] != venture_id:
            raise ValueError('Document not found in this venture')
        return document

    def revisions(self, venture_id, doc_id):
        self.get(venture_id, doc_id)
        return sorted([r for r in self.store.all('venture_document_revisions')
                       if r['venture_id'] == venture_id and r['document_id'] == doc_id],
                      key=lambda r: r['version'])

    def resolve(self, venture_id, document_id=None, document_name=None):
        """Resolve an exact local selector; never guess or repair identifiers."""
        self._venture(venture_id)
        guidance = 'Use venture_document_list, then retry with the exact document_name or document_id. No change was made.'
        if document_id is None and document_name is None:
            raise ValueError('A document_name or document_id is required. ' + guidance)
        if document_id is not None and (not isinstance(document_id, str) or not document_id or len(document_id) > 200):
            raise ValueError('Invalid document_id. ' + guidance)
        if document_name is not None and (not isinstance(document_name, str) or not document_name or len(document_name) > 200):
            raise ValueError('Invalid document_name. ' + guidance)
        document = None
        if document_id is not None:
            document = self.store.get('venture_documents', document_id)
            if not document or document['venture_id'] != venture_id:
                raise ValueError('Document not found in this venture. ' + guidance)
        if document_name is not None:
            matches = [doc for doc in self.list(venture_id) if doc['name'].casefold() == document_name.casefold()]
            if len(matches) != 1:
                raise ValueError('Document name not found uniquely in this venture. ' + guidance)
            if document is not None and document['id'] != matches[0]['id']:
                raise ValueError('Document selectors do not match. ' + guidance)
            document = matches[0]
        return document
