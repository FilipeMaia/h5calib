#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <H5PLextern.h>


#define H5Z_FILTER_CALIB 57836

static size_t H5Z_filter_calib(unsigned int flags, size_t cd_nelmts,
			       const unsigned int cd_values[], size_t nbytes,
			       size_t *buf_size, void **buf);

#define CACHE_CALIB

#define PEDESTAL_v1 0x00010001ull
#define AGIPD_v1 0x00020001ull
#define AGIPD_v2 0x00020002ull
#define H5CALIB_MAGIC 0x6290D662ull

const H5Z_class2_t H5Z_calib[1] = {
  {
    /* H5Z_class_t version */
    H5Z_CLASS_T_VERS,
    /* Filter id number */
    (H5Z_filter_t)H5Z_FILTER_CALIB,
    /* encoder_present flag (set to true) */
    1, 
    /* decoder_present flag (set to true) */
    1, 
    /* Filter name for debugging    */
    "HDF5 Calib filter; see http://www.hdfgroup.org/services/contributions.html", 
    /* The "can apply" callback     */
    NULL, 
    /* The "set local" callback     */
    NULL, 
    /* The actual filter function   */
    (H5Z_func_t)H5Z_filter_calib, 
  }
};

H5PL_type_t H5PLget_plugin_type(void){
  return H5PL_TYPE_FILTER;
}

const void *H5PLget_plugin_info(void) {
  return H5Z_calib;
}

typedef struct calib_config_t {
  int config_str_len;
  char * raw_path;
  char * calib_path;
  uint32_t file_magic;
  uint32_t calib_alg;
  hsize_t image_id;
  hsize_t * calib_shape;
  int calib_shape_len;
  void * alg_config;
} calib_config_t;

typedef struct AGIPD_v1_config_t{
  hsize_t cell_id;
} AGIPD_v1_config_t;

/* For now we can use the same config for v1 and v2 */
typedef AGIPD_v1_config_t AGIPD_v2_config_t;

typedef struct dataset_cache_t {
  char * path;
  hid_t dataset;
  hsize_t dims[4];
  int ndims;
  /* pointer to the read data in memory */
  float * data;
} dataset_cache_t;

/* Static variables are initialized to zero so we can test to check if path is NULL */
static dataset_cache_t raw_cache;
static dataset_cache_t calib_cache;


static hid_t find_calib_file(int id, uint32_t file_magic){
  ssize_t n = H5Fget_obj_count((hid_t)H5F_OBJ_ALL, H5F_OBJ_FILE);
  hid_t * obj_id_list = (hid_t *)malloc(sizeof(hid_t)*n);
  hid_t ret = 0;
  H5Fget_obj_ids((hid_t)H5F_OBJ_ALL,H5F_OBJ_FILE,n,obj_id_list);
  for(int i = 0; i < n; i++){
    if(H5Aexists(obj_id_list[i], "h5calib_file_magic")){
      hid_t attr = H5Aopen(obj_id_list[i], "h5calib_file_magic", H5P_DEFAULT);
      uint32_t magic;     
      H5Aread(attr, H5T_NATIVE_UINT, &magic);
      if(magic == file_magic){
	ret = obj_id_list[i];
      }
    }
  }
  if(ret == 0){
    fprintf(stderr, "h5calib error: Could not find file with attribute h5calib_file_magic = %ul", file_magic);
  }
  free(obj_id_list);
  return ret;
}

static calib_config_t str_to_config(void * p){
  calib_config_t ret;
  ret.config_str_len = 0;
  /* First check for the h5calib magic */
  uint32_t * u = (uint32_t *)p;
  if(u[0] != H5CALIB_MAGIC){
    return ret;
  }
  /* Now get the dataset magic and the calibration algorithm number */
  ret.file_magic = u[1];
  ret.calib_alg = u[2];

  if(ret.calib_alg == PEDESTAL_v1){
    ret.alg_config = NULL;
    ret.image_id = u[3];
    ret.calib_shape = malloc(sizeof(hsize_t)*3);
    ret.calib_shape_len = 3;
    ret.calib_shape[0] = 1;
    ret.calib_shape[1] = u[4];
    ret.calib_shape[2] = u[5];
    /* and finally the raw and calib paths */
    char * s = (char *)(u+6);
    ret.raw_path = strdup(s);
    s += strlen(ret.raw_path)+1;
    ret.calib_path = strdup(s);
    s += strlen(ret.calib_path)+1;
    /* calculate all the space this takes */
    ret.config_str_len = s-(char *)p;

  /* Currently we only have one calibration algorithm, AGIPD_v1 */
  }else if(ret.calib_alg == AGIPD_v1){
    ret.alg_config = malloc(sizeof(AGIPD_v1_config_t));
    /* get cell_id, image_id and calibration_shape */
    ((AGIPD_v1_config_t *)ret.alg_config)->cell_id = u[3];
    ret.image_id = u[4];
    ret.calib_shape = malloc(sizeof(hsize_t)*3);
    ret.calib_shape_len = 3;
    ret.calib_shape[0] = u[5];
    ret.calib_shape[1] = u[6];
    ret.calib_shape[2] = u[7];
    /* and finally the raw and calib paths */
    char * s = (char *)(u+8);
    ret.raw_path = strdup(s);
    s += strlen(ret.raw_path)+1;
    ret.calib_path = strdup(s);
    s += strlen(ret.calib_path)+1;
    /* calculate all the space this takes */
    ret.config_str_len = s-(char *)p;
  }else if(ret.calib_alg == AGIPD_v2){
    ret.alg_config = malloc(sizeof(AGIPD_v2_config_t));
    /* get cell_id, image_id and calibration_shape */
    ((AGIPD_v2_config_t *)ret.alg_config)->cell_id = u[3];
    ret.image_id = u[4];
    ret.calib_shape = malloc(sizeof(hsize_t)*4);
    ret.calib_shape_len = 4;
    ret.calib_shape[0] = u[5];
    ret.calib_shape[1] = u[6];
    ret.calib_shape[2] = u[7];
    ret.calib_shape[3] = 8;
    /* and finally the raw and calib paths */
    char * s = (char *)(u+8);
    ret.raw_path = strdup(s);
    s += strlen(ret.raw_path)+1;
    ret.calib_path = strdup(s);
    s += strlen(ret.calib_path)+1;
    /* calculate all the space this takes */
    ret.config_str_len = s-(char *)p;
  }else{
    fprintf(stderr, "h5calib error: Unknown calibration algorithm - %ul\n", ret.calib_alg);
  }
  return ret;
}

static void setup_cache(calib_config_t ret){  
  /* 
     Refill cache if the cache has not been initialized or it has been
     with a different path 
  */
  if(raw_cache.path == NULL || /* The cache has not yet been initialized */
     strcmp(ret.raw_path,raw_cache.path) != 0 || /* The cache has been initialized
						    with a different dataset */
     H5Iis_valid(raw_cache.dataset) <= 0){ /* The dataset that was cached is no 
					      longer valid (e.g. file was closed) */
    hid_t file = find_calib_file(0, ret.file_magic);
    printf("Reading raw %s from %lld\n", ret.raw_path, file);
    hid_t dataset = H5Dopen(file,ret.raw_path,H5P_DEFAULT);
    hid_t ds = H5Dget_space(dataset);
    raw_cache.ndims = H5Sget_simple_extent_ndims(ds);
    if(raw_cache.ndims == 3 || raw_cache.ndims == 4){
      H5Sget_simple_extent_dims(ds, raw_cache.dims, NULL);
    }else{
      exit(-1);
    }
    free(raw_cache.path);
    raw_cache.path = strdup(ret.raw_path);
    raw_cache.dataset = dataset;
  }

  /* 
     Refill cache is the cache has not been initialized or it has been
     with a different path 
  */
  if(calib_cache.path == NULL || /* The cache has not yet been initialized */
     strcmp(ret.calib_path,calib_cache.path) != 0 || /* The cache has been initialized
							with a different dataset */
     H5Iis_valid(calib_cache.dataset) <= 0){ /* The dataset that was cached is no 
						longer valid (e.g. file was closed) */
    hid_t file = find_calib_file(0, ret.file_magic);
    printf("Reading calib %s from %lld\n", ret.calib_path, file);
    hid_t dataset = H5Dopen(file,ret.calib_path,H5P_DEFAULT);
    free(calib_cache.path);
    calib_cache.path = strdup(ret.calib_path);
    calib_cache.dataset = dataset;
#ifdef CACHE_CALIB
    free(calib_cache.data);
    hid_t ds = H5Dget_space(dataset);
    hsize_t calib_len = H5Sget_simple_extent_npoints(ds);
    calib_cache.data = (float *)malloc(sizeof(float)*calib_len);
    H5Dread(calib_cache.dataset, H5T_NATIVE_FLOAT, H5S_ALL, H5S_ALL, H5P_DEFAULT, calib_cache.data);
#endif
  }
}


static float * read_raw(calib_config_t conf){
  /* We're assuming CACHE_CALIB here */
  int image_size = conf.calib_shape[1]*conf.calib_shape[2];
  if(conf.calib_alg == PEDESTAL_v1 || conf.calib_alg == AGIPD_v1){
    float * raw_data = malloc(sizeof(float)*conf.calib_shape[1]*conf.calib_shape[2]);
    hsize_t start[3] = {conf.image_id,0,0};
    hsize_t count[3] = {1, conf.calib_shape[1], conf.calib_shape[2]};
    hid_t mem_ds = H5Screate_simple(3,count,count);
    hid_t file_ds = H5Dget_space(raw_cache.dataset);
    H5Sselect_hyperslab(file_ds, H5S_SELECT_SET, start, NULL, count, NULL);
    H5Dread(raw_cache.dataset, H5T_NATIVE_FLOAT, mem_ds, file_ds, H5P_DEFAULT, raw_data);
    return raw_data;
  }else  if(conf.calib_alg == AGIPD_v2){
    float * raw_data = malloc(sizeof(float)*conf.calib_shape[1]*conf.calib_shape[2]*2);
    hsize_t start[4] = {conf.image_id,0,0,0};
    hsize_t count[4] = {1, conf.calib_shape[1], conf.calib_shape[2],2};
    hid_t mem_ds = H5Screate_simple(4,count,count);
    hid_t file_ds = H5Dget_space(raw_cache.dataset);
    H5Sselect_hyperslab(file_ds, H5S_SELECT_SET, start, NULL, count, NULL);
    H5Dread(raw_cache.dataset, H5T_NATIVE_FLOAT, mem_ds, file_ds, H5P_DEFAULT, raw_data);
    return raw_data;
  }else{
    fprintf(stderr,"Unknown calibration algorthm\n");
  }
  return NULL;
}

static void apply_calibration(float * raw_data, float * calib_data, calib_config_t conf){
  /* We're assuming CACHE_CALIB here */
  int image_size = conf.calib_shape[1]*conf.calib_shape[2];
  if(conf.calib_alg == PEDESTAL_v1){
    for(int i = 0; i<image_size; i++){
      raw_data[i] -= calib_cache.data[i];
    }
  }else  if(conf.calib_alg == AGIPD_v1){
    AGIPD_v1_config_t alg_conf = *((AGIPD_v1_config_t *)conf.alg_config);
    for(int i = 0; i<image_size; i++){
      raw_data[i] -= calib_cache.data[alg_conf.cell_id*image_size+i];
    }
  }else  if(conf.calib_alg == AGIPD_v2){
    AGIPD_v2_config_t alg_conf = *((AGIPD_v2_config_t *)conf.alg_config);
    for(int i = 0; i<image_size; i++){
      float signal = raw_data[i*2];
      float gain = raw_data[i*2 + 1];
      hsize_t offset = (alg_conf.cell_id*image_size+i)*8;
      int gain_level = 0;
      if(gain > calib_cache.data[offset]){
	gain_level = 1;
      }
      if(gain > calib_cache.data[offset+1]){
	gain_level = 2;
      }
      signal -= calib_cache.data[offset+2+gain_level*2];
      signal /= calib_cache.data[offset+3+gain_level*2];

      /* Write out the resulting signal. We're gonna overwrite the raw data */
      raw_data[i] = signal;
    }
  }
}
 
/* flags defines the direction of the filter
   cd_nelmts is the number of user defined values
   cd_values are the user defined values
   nbytes is the size of the input
   buf_size must contain the size of the output when returning
   *buf points to the input data at the start and should be set
   to point to the output data before returning. 
   N.B. The input data should be freed before returning.

   This filter requires 3 compression options (cd_values) corresponding
   to the image height, image width and nbytes per element in the dataset.
*/
static size_t H5Z_filter_calib(unsigned int flags, size_t cd_nelmts,
			       const unsigned int cd_values[], size_t nbytes,
			       size_t *buf_size, void **buf){
  char *output_buffer = NULL;

  if (flags & H5Z_FLAG_REVERSE) {
    /* Read out calibrated data */
    // All the magic will happen here
    calib_config_t conf = str_to_config(*buf);
    setup_cache(conf);
    float * c = *buf;
    float * raw_data = read_raw(conf);
    output_buffer = (char *)raw_data;
    apply_calibration(raw_data, calib_cache.data, conf);
#ifndef NDEBUG
    fprintf(stdout,"[debug] h5calib: decompressed %zu bytes\n",*buf_size);
#endif
  }else{
    /* Write out data necessary for calibration */

    /* The first part of the data contains the path to the raw dataset
       Let's parse it
     */
    calib_config_t conf = str_to_config(*buf);
    if(conf.config_str_len == 0){
      fprintf(stderr, "h5calib warning: Cannot write to read-only dataset\n");
      
    }else{
      *buf_size = conf.config_str_len;
      output_buffer = malloc(sizeof(char)*(*buf_size));
      memcpy(output_buffer,*buf,*buf_size);
#ifndef NDEBUG
      fprintf(stdout, "[debug] h5calib: encoded %zu bytes into %zu bytes for a ratio of %f\n", nbytes, *buf_size, ((float)*buf_size)/nbytes);
#endif
    }
  }
  if(!output_buffer){
    return 0;
  }
  free(*buf);
  *buf = output_buffer;
  return *buf_size;
}
