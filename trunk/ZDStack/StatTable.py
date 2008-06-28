from threading import Lock

class StatTable:

    """StatTable is a table of columns and rows.

    StatTable can export its data as a list of dicts or a
    CSV-formatted string.  Columns must be strings.

    """

    def __init__(self, columns=[], rows=[]):
        self.columns = []
        self.rows = []
        for column in columns:
            self.add_column(column)
        for row in rows:
            self.add_row(row)
        self.lock = Lock()

    def _validate_row(self, row):
        """Validates a row.

        row: a dict or sequence to be validated

        """
        if isinstance(row, dict):
            invalid_columns = [x for x in dict if x not in self.columns]
            if invalid_columns:
                invalid_columns = ', '.join(invalid_columns)
                raise ValueError("Invalid columns: %s" % (s))
        elif not len(row) == len(self.columns):
            s = "Number of values and number of columns do not match"
            raise ValueError(s)

    def _validate_column(self, column):
        """Validates a column.

        column: a string to be validated

        """
        if column in self.columns:
            raise ValueError("%s is already present in columns" % (column))
        if not isinstance(column, str):
            raise ValueError("Columns must be strings")

    def _insert_value(self, s, value, index):
        """Inserts a value into a sequence.

        s:     a sequence in which to insert a value
        value: the value to insert
        index: the index at which to insert the value

        """
        a = s[:index]
        b = s[index:]
        return a + [value] + b

    def _move_value(self, s, old_index, new_index):
        """Moves a value in a sequence.

        s:         a sequence in which to move values
        old_index: an int representing the index of the value to move
        new_index: an int representing the index to move the value to

        """
        if new_index > old_index:
            x = [old_index, new_index]
        else:
            x = [new_index, old_index]
        a = s[:x[0]]
        b = s[x[0]:][:x[1] - old_index]
        c = s[x[0]:][x[1] - old_index:]
        if new_index > old_index:
            return a + b[1:] + [b[0]] + c
        else:
            return a + [c[0]] + b + c[1:]
        
    def _swap_value(self, s, old_index, new_index):
        """Moves a value in a sequence.

        s:         a sequence in which to move values
        old_index: an int representing the index of the value to move
        new_index: an int representing the index to move the value to

        """
        if old_index > new_index:
            x = [new_index, old_index]
        else:
            x = [old_index, new_index]
        a = s[:x[0]]
        b = s[x[0]:][:x[1] - old_index]
        c = s[x[0]:][x[1] - old_index:]
        return a + [c[0]] + b[1:] + [b[0]] + c[1:]

    def _row_to_csv_line(self, row):
        """Converts a row to a CSV-formatted record.

        row: a sequence

        """
        out = []
        for x in row:
            if x is None:
                out.append('')
            else:
                out.append(x.replace('\n', '\\n'))
        return '","'.join(out).join(['"', '"'])
        
    def add_row(self, row):
        """Adds a row to self.rows.

        row: a dict mapping columns to values or a sequence of values

        """
        self._validate_row(row)
        if isinstance(row, dict):
            r = []
            for c in self.columns:
                if c in row:
                    r.append(row[c])
                else:
                    r.append(None)
            to_append = r
        else:
            to_append = row
        self.lock.acquire()
        try:
            self.rows.append(row)
        finally:
            self.lock.release()

    def remove_row(self, index):
        """Removes a row from self.rows.

        index: an int representing the index of the row to remove

        """
        if index > len(self.rows) - 1:
            raise ValueError("Index exceeds number of rows")
        self.lock.acquire()
        try:
            del self.rows[index]
        finally:
            self.lock.release()

    def insert_row(self, row, index):
        """Inserts a row into self.rows.

        row:  a dict mapping columns to values or a sequence of values
        index: an int representing the index at which to insert row

        """
        self._validate_row(row)
        self.lock.acquire()
        try:
            self.rows = _insert_value(self.rows, row, index)
        finally:
            self.lock.release()

    def move_row(self, old_index, new_index):
        """Moves a row from one spot to another.

        old_index: an int representing the index of the row to move
        new_index: an int representing the index to move the row to

        """
        self.lock.acquire()
        try:
            self.rows = self._move_value(self.rows, old_index, new_index)
        finally:
            self.lock.release()

    def set_row(self, index, row):
        """Sets a row to self.rows.

        index: an int representing the index of the row to set
        row:   a dict mapping columns to values or a sequence of values

        """
        self._validate_row(row)
        self.lock.acquire()
        try:
            self.rows[index] = row
        finally:
            self.lock.release()

    def add_column(self, column):
        """Adds a column to self.columns.

        column: a string representing a column to add

        """
        self._validate_column(column)
        self.lock.acquire()
        try:
            self.columns.append(column)
            for row in self.rows:
                row.append(None)
        finally:
            self.lock.release()

    def remove_column(self, column):
        """Removes a column from self.columns.

        column: a string representing the column to remove

        """
        index = self.columns.index(column)
        self.lock.acquire()
        try:
            del self.columns[index]
            for row in self.rows:
                del row[index]
        finally:
            self.lock.release()

    def rename_column(self, old_name, new_name):
        """Renames a column.

        old_name: a string representing the name of the column to
                  rename
        new_name: a string representing the new name of the column

        """
        old_index = self.columns.index(old_name)
        self.lock.acquire()
        try:
            self.columns[old_index] = new_name
        finally:
            self.lock.release()

    def move_column(self, name, new_index):
        """Moves a column.

        column:    a string representing the name of the column to move
        new_index: an int representing the index to move the column to

        """
        old_index = self.columns.index(column)
        self.lock.acquire()
        try:
            self.columns = self._move_value(self.columns, old_index, new_index)
            for row in self.rows:
                row = self._move_value(row, old_index, new_index)
        finally:
            self.lock.release()

    def insert_column(self, column, index):
        """Inserts a column into self.columns.

        column: a string representing the column to insert
        index:  an int representing the index to insert the column at.

        """
        self.lock.acquire()
        try:
            self.columns = self._insert_value(self.columns, column, index)
            for row in self.rows:
                row = self._insert_value(row, None, index)
        finally:
            self.lock.release()

    def export_dicts(self):
        """Exports this table's data as a list of dicts."""
        return [dict(zip(self.columns, r)) for r in self.rows]

    def export_csv(self):
        """Exports this table's data as a CSV-formatted string."""
        header = '\n'.join(self._row_to_csv_line(self.columns))
        body = '\n'.join([self._row_to_csv_line(r) for r in self.rows])
        return '\n'.join([header, body])

