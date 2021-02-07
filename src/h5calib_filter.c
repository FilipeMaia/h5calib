#include <stdlib.h>
#include <string.h>
#include <H5PLextern.h>


#define H5Z_FILTER_CALIB 57836

static size_t H5Z_filter_calib(unsigned int flags, size_t cd_nelmts,
			       const unsigned int cd_values[], size_t nbytes,
			       size_t *buf_size, void **buf);

#define CACHE_CALIB

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
  hsize_t cell_id;
  hsize_t image_id;
  hsize_t * calib_shape;  
} calib_config_t;

typedef struct dataset_cache_t {
  char * path;
  hid_t dataset;
  hsize_t dims[3];
  /* pointer to the read data in memory */
  float * data;
} dataset_cache_t;

/* Static variables are initialized to zero so we can test to check if path is NULL */
static dataset_cache_t raw_cache;
static dataset_cache_t calib_cache;


static hid_t find_calib_file(int id){
  ssize_t n = H5Fget_obj_count((hid_t)H5F_OBJ_ALL, H5F_OBJ_FILE);
  hid_t * obj_id_list = (hid_t *)malloc(sizeof(hid_t)*n);
  hid_t ret = 0;
  H5Fget_obj_ids((hid_t)H5F_OBJ_ALL,H5F_OBJ_FILE,n,obj_id_list);
  if(n == 1){
    ret = obj_id_list[0];
  }else{
    printf("number of open files %zd\n", n);
  }
  free(obj_id_list);
  return ret;
}

static char * get_dataset_path(float * c){
  int len = 0;
  float * s = c;
  while(*c != -1){
    c++;
    len++;
  }
  
  char * path = (char *)malloc(sizeof(char)*(len+1));
  c = s;
  for(int i = 0;i<len;i++){
    path[i] = *c;
    c++;
  }
  /* zero terminate path */
  path[len] = 0;

  return path;
}

static hsize_t * get_calib_shape(float * c){
  int len = 0;
  float * s = c;


  while(*c != -1){
    c++;
    len++;
  }
  
  hsize_t * shape = (hsize_t *)malloc(sizeof(hsize_t)*(len));
  c = s;
  for(int i = 0;i<len;i++){
    shape[i] = *c;
    c++;
  }
  return shape;
}

static calib_config_t str_to_config(float * c){
  calib_config_t ret;
  ret.config_str_len = 0;
  /* The first part of the data contains the path to the raw dataset
     Let's parse it
  */
  char * path = get_dataset_path(c);
  /* increment c to the start of the next dataset */
  ret.config_str_len += strlen(path)+1;
  c += strlen(path)+1;
  ret.raw_path = path;

  /* The second part of the data contains the path to the calibration constants dataset
     Let's parse it
  */
  path = get_dataset_path(c);
  /* increment c to the start of the next dataset */
  ret.config_str_len += strlen(path)+1;
  c += strlen(path)+1;
  ret.calib_path = path;


  ret.cell_id = *c;
  c++;
  ret.image_id = *c;
  c++;
  ret.calib_shape = get_calib_shape(c);
  /* 3 for the image_shape 3 for cell_id, image_id plus 1 for the closing -1 */
  ret.config_str_len += 6;
  return ret;
}

static void setup_cache(calib_config_t ret){  
  /* 
     Refill cache if the cache has not been initialized or it has been
     with a different path 
  */
  if(raw_cache.path == NULL || strcmp(ret.raw_path,raw_cache.path) != 0){
    hid_t file = find_calib_file(0);
    printf("Reading %s from %lld\n", ret.raw_path, file);
    hid_t dataset = H5Dopen(file,ret.raw_path,H5P_DEFAULT);
    hid_t ds = H5Dget_space(dataset);
    if(H5Sget_simple_extent_ndims(ds) == 3){
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
  if(calib_cache.path == NULL || strcmp(ret.calib_path,calib_cache.path) != 0){
    hid_t file = find_calib_file(0);
    //hid_t file = H5Fopen("/Users/filipe/src/h5calib/tests/comp.h5",H5F_ACC_RDONLY,H5P_DEFAULT);
    hid_t dataset = H5Dopen(file,ret.calib_path,H5P_DEFAULT);
    free(calib_cache.path);
    calib_cache.path = strdup(ret.calib_path);
    calib_cache.dataset = dataset;
#ifdef CACHE_CALIB
    free(calib_cache.data);
    calib_cache.data = (float *)malloc(sizeof(float)*ret.calib_shape[0]*ret.calib_shape[1]*ret.calib_shape[2]);
    H5Dread(calib_cache.dataset, H5T_NATIVE_FLOAT, H5S_ALL, H5S_ALL, H5P_DEFAULT, calib_cache.data);
#endif
  }
}


static void apply_calibration(float * raw_data, float * calib_data, calib_config_t conf){
  int image_size = conf.calib_shape[1]*conf.calib_shape[2];
  for(int i = 0; i<image_size; i++){
    raw_data[i] -= calib_cache.data[conf.cell_id*image_size+i];
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
    output_buffer = malloc(sizeof(float)*conf.calib_shape[1]*conf.calib_shape[2]);
    float * raw_data = (float *) output_buffer;
    hsize_t start[3] = {conf.image_id,0,0};
    hsize_t count[3] = {1, conf.calib_shape[1], conf.calib_shape[2]};
    hid_t mem_ds = H5Screate_simple(3,count,count);
    hid_t file_ds = H5Dget_space(raw_cache.dataset);
    H5Sselect_hyperslab(file_ds, H5S_SELECT_SET, start, NULL, count, NULL);
    H5Dread(raw_cache.dataset, H5T_NATIVE_FLOAT, mem_ds, file_ds, H5P_DEFAULT, raw_data);
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
    *buf_size = sizeof(float)*conf.config_str_len;
    output_buffer = malloc(sizeof(char)*(*buf_size));
    memcpy(output_buffer,*buf,*buf_size);
#ifndef NDEBUG
    fprintf(stdout, "[debug] h5calib: encoded %zu bytes into %zu bytes for a ratio of %f\n", nbytes, *buf_size, ((float)*buf_size)/nbytes);
#endif
  }
  if(!output_buffer){
    return 0;
  }
  free(*buf);
  *buf = output_buffer;
  return *buf_size;
}
