#ifndef OBSERVATION_H
#define OBSERVATION_H

#include <string>
#include "Statistics.h"

class Observation {
public:
    // Format statistical features into the standard JSON schema
    static std::string build_json(const AggregatedStats& stats, 
                                  const std::string& anchor_id, 
                                  const std::string& target_mac, 
                                  uint64_t timestamp_ms);
};

#endif // OBSERVATION_H
