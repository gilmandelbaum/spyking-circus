import h5py, numpy
import ConfigParser as configparser

class DataFile(object):

    def __init__(self, file_name, params):
        self.file_name = file_name
        assert isinstance(params, configparser.ConfigParser)
        self.params = params
        self.N_e    = params.getint('data', 'N_e')
        self.N_tot  = params.getint('data', 'N_total')
        self.rate   = params.getint('data', 'sampling_rate')
        self.template_shift = params.getint('data', 'template_shift')

    def get_data(self, idx, chunk_len, chunk_size=None, padding=(0, 0), nodes=None):
        pass

    def set_data(self, block):
        pass

    def analyze(self):
        pass

    def prepare_preview(self):
    	pass

    def close(self):
        pass

    def set_offset(self, data_dtype):
   		self.dtype_offset = self.params.get('data', 'dtype_offset')
    	if self.dtype_offset == 'auto':
	        if self.data_dtype == 'uint16':
	            self.dtype_offset = 32767
	        elif self.data_dtype == 'int16':
	            self.dtype_offset = 0
	        elif self.data_dtype == 'float32':
	            self.dtype_offset = 0
	        elif self.data_dtype == 'int8':
	            self.dtype_offset = 0        
	        elif self.data_dtype == 'uint8':
	            self.dtype_offset = 127
		else:
			try:
				self.dtype_offset = self.params.getint('data', 'dtype_offset')
			except Exception:
				print "Offset not valid"


class RawBinaryFile(DataFile):

    def __init__(self, file_name, params):
        DataFile.__init__(self, file_name, params)
        self.data_offset = 0
        self.data_dtype  = self.params.get('data', 'data_dtype')
        self.set_offset(self.data_dtype)

    def get_data(self, idx, chunk_len, chunk_size=None, padding=(0, 0), nodes=None):
    	
		if chunk_size is None:
		    chunk_size = self.params.getint('data', 'chunk_size')

		self.data    = numpy.memmap(self.file_name, offset=self.data_offset, dtype=self.data_dtype, mode='r')
		local_chunk  = self.data[idx*numpy.int64(chunk_len)+padding[0]:(idx+1)*numpy.int64(chunk_len)+padding[1]]
		del self.data
		local_shape  = chunk_size + (padding[1]-padding[0])//self.N_tot
		local_chunk  = local_chunk.reshape(local_shape, self.N_tot)
		local_chunk  = local_chunk.astype(numpy.float32)
		local_chunk -= self.dtype_offset
		if nodes is not None:
		    if not numpy.all(nodes == numpy.arange(self.N_tot)):
		        local_chunk = numpy.take(local_chunk, nodes, axis=1)
		return numpy.ascontiguousarray(local_chunk), local_shape

    def set_data(self, offset, data):
        self.data      = numpy.memmap(self.file_name, offset=self.data_offset, dtype=self.data_dtype, mode='r+')
        data  += self.dtype_offset
        data   = data.astype(data_dtype)
        data   = data.ravel()
        self.data[offset:offset+len(data)] = data
        del self.data

    def analyze(self, chunk_size=None):

	    if chunk_size is None:
	        chunk_size = self.params.getint('data', 'chunk_size')
	    
	    chunk_len      = numpy.int64(self.N_tot) * chunk_size
	    borders        = numpy.int64(self.N_tot) * self.template_shift
	    self.data      = numpy.memmap(self.file_name, offset=self.data_offset, dtype=self.data_dtype, mode='r')
	    N              = len(self.data)
	    del self.data
	    nb_chunks      = numpy.int64(N) // chunk_len
	    last_chunk_len = N - nb_chunks * chunk_len
	    last_chunk_len = self.N_tot * numpy.int64(last_chunk_len)//self.N_tot
	    
	    return borders, nb_chunks, chunk_len, last_chunk_len

    def copy_header(self, file_in, file_out):
	    fin  = open(file_in, 'rb')
	    fout = open(file_out, 'wb')
	    data = fin.read(self.data_offset)
	    fout.write(data)
	    fin.close()
	    fout.close()

    def prepare_preview(self, preview_filename):
	    chunk_size   = 2*self.rate
	    chunk_len    = numpy.int64(self.N_tot) * chunk_size
	    self.data    = numpy.memmap(self.file_name, offset=self.data_offset, dtype=self.data_dtype, mode='r')
	    local_chunk  = self.data[0:chunk_len]
	    del self.data

	    output = open(preview_filename, 'wb')
	    fid    = open(self.file_name, 'rb')
	    # We copy the header 
	    for i in xrange(self.data_offset):
	        output.write(fid.read(1))
	    fid.close()

	    #Then the datafile
	    local_chunk.tofile(output)
	    output.close()

	def close():
		self.data.flush()


class RawMCSFile(RawBinaryFile):

    def __init(self, datapath, params):
        DataFile.__init__(self, file_name, params)
        self.data_offset = detect_header()[0]

    def analyze(self, chunk_size=None):
        if params.getboolean('data', 'MCS'):
	        self.data_offset, _ = self.detect_header()
        return RawDataFile.analyze(self, chunk_size)

    def detect_header():
	    try:
	        header      = 0
	        stop        = False
	        fid         = open(self.file_name, 'rb')
	        header_text = ''
	        regexp      = re.compile('El_\d*')

	        while ((stop is False) and (header <= 5000)):
	            header      += 1
	            char         = fid.read(1)
	            header_text += char.decode('Windows-1252')
	            if (header > 2):
	                if (header_text[header-3:header] == 'EOH'):
	                    stop = True
	        fid.close()
	        if stop is False:
	        #    print_error(['Wrong MCS header: file is not exported with MCRack'])
	            sys.exit(0) 
	        else:
	            header += 2
	        return header, len(regexp.findall(header_text))
	    except Exception:
	        #print_error(["Wrong MCS header: file is not exported with MCRack"])
	        sys.exit(0)




class H5File(DataFile):

    def __init__(self, file_name, params):
        DataFile.__init__(self, file_name, params)
        self.h5_key = self.params.get('data', 'hdf5_key_data')
        self.my_file = h5py.File(self.file_name, mode='r+')
        self.data_dtype = self.my_file.get(self.h5_key).dtype
        self.set_offset(self.data_dtype)
        self.data = self.my_file.get(self.h5_key)
        assert (self.data.shape[0] == self.N_tot) or (self.data.shape[1] == self.N_tot)
        if self.data.shape[0] == self.N_tot:
        	self.time_axis = 1
        else:
        	self.time_axis = 0

    def get_data(self, idx, chunk_len, chunk_size=None, padding=(0, 0), nodes=None):
        if chunk_size is None:
            chunk_size = self.params.getint('data', 'chunk_size')

        if self.time_axis == 0:
            local_chunk = self.data[idx*numpy.int64(chunk_len)+padding[0]:(idx+1)*numpy.int64(chunk_len)+padding[1], :]
        elif self.time_axis == 1:
            local_chunk = self.data[:, idx*numpy.int64(chunk_len)+padding[0]:(idx+1)*numpy.int64(chunk_len)+padding[1]].T

        local_chunk  = local_chunk.astype(numpy.float32)
        local_chunk -= self.dtype_offset
        local_shape  = chunk_size + (padding[1]-padding[0])//self.N_tot

        if nodes is not None:
            if not numpy.all(nodes == numpy.arange(self.N_tot)):
                local_chunk = numpy.take(local_chunk, nodes, axis=1)

        return numpy.ascontiguousarray(local_chunk), local_shape

    def set_data(self, offset, data):
        
    	data += self.dtype_offset
    	data  = data.astype(self.data_dtype)

        if self.time_axis == 0:
            local_chunk = self.data[offset:offset+data.shape[0], :] = data
        elif self.time_axis == 1:
            local_chunk = self.data[:, offset:offset+data.shape[0]] = data.T

    def analyze(self, chunk_size=None):

	    if chunk_size is None:
	        chunk_size = self.params.getint('data', 'chunk_size')
	    
	    chunk_len      = chunk_size
	    borders        = self.template_shift
	    size           = self.my_file.get(self.h5_key).shape
	    nb_chunks      = numpy.int64(size[self.time_axis]) // chunk_len
	    last_chunk_len = size[self.time_axis] - nb_chunks * chunk_len
	    
	    return borders, nb_chunks, chunk_len, last_chunk_len

    def prepare_preview(self, preview_filename):
	    chunk_size   = 2*self.rate
	    chunk_len    = numpy.int64(self.N_tot) * chunk_size
	    self.data    = numpy.memmap(self.file_name, offset=self.data_offset, dtype=self.data_dtype, mode='r')
	    local_chunk  = self.data[0:chunk_len]
	    del self.data

	    output = open(preview_filename, 'wb')
	    fid    = open(self.file_name, 'rb')
	    # We copy the header 
	    for i in xrange(self.data_offset):
	        output.write(fid.read(1))
	    fid.close()

	    #Then the datafile
	    local_chunk.tofile(output)
	    output.close()

    def close(self):
        self.my_file.close()

